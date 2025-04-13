import os
import json
import re
import requests
from dotenv import load_dotenv
from geo import get_coordinates
from prompts import weather_user_prompt, SYSTEM_PROMPT, ROLE_SYSTEM, ROLE_USER
from os import getenv
from datetime import date, datetime, timedelta, time

load_dotenv()

API_KEY = getenv("OPENAI_API_KEY")
API_URL = getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = getenv("OPENROUTER_MODEL", "deepseek/deepseek-v3-base:free")

def extract_json_from_text(text: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Warning: Found JSON block, but failed to parse: {e}")

    braces = 0
    start_idx = None
    potential_matches = []
    for i, char in enumerate(text):
        if char == '{':
            if braces == 0:
                start_idx = i
            braces += 1
        elif char == '}':
            if braces > 0:
                braces -= 1
                if braces == 0 and start_idx is not None:
                    potential_matches.append(text[start_idx:i+1])
                    start_idx = None

    potential_matches.sort(key=len, reverse=True)
    for json_str in potential_matches:
        try:
            parsed = json.loads(json_str)
            if "location" in parsed and "date_from" in parsed:
                 return parsed
        except json.JSONDecodeError:
            continue

    raise ValueError("No valid JSON object matching expected structure found in model response.")

def transform_query_to_json(query: str, api_counts: dict) -> dict:
    user_message_content = weather_user_prompt.format(query=query)
    messages = [
        {"role": ROLE_SYSTEM, "content": SYSTEM_PROMPT},
        {"role": ROLE_USER, "content": user_message_content}
    ]

    print(f"--- Sending to LLM ({MODEL}) ---")
    print(f"User Message: {user_message_content.strip()}")
    print("-" * 20)

    api_counts["llm"] += 1
    print(f"  [API Call] Incrementing LLM count to: {api_counts['llm']}")

    raw_response_text = None
    response_status_code = None

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": getenv("YOUR_SITE_URL", "http://localhost"),
                "X-Title": getenv("YOUR_APP_NAME", "Weather Chatbot"),
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 300,
            },
            timeout=45
        )
        response_status_code = response.status_code
        raw_response_text = response.text

        print(f"--- LLM API Response ---")
        print(f"Status Code: {response_status_code}")
        print(f"Raw Body Text:\n<<<\n{raw_response_text}\n>>>")
        print("-" * 20)

        response.raise_for_status()

        result = response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error calling LLM API: {e}")
        if raw_response_text is not None:
             print(f"Raw response text before error: {raw_response_text}")
        raise RuntimeError(f"API call failed: {e}") from e
    except json.JSONDecodeError as e:
         print(f"Error: API returned status {response_status_code} but body is not valid JSON.")
         print(f"JSONDecodeError: {e}")
         raise RuntimeError(f"API response was not valid JSON (status {response_status_code})") from e

    if "choices" not in result or not result["choices"]:
        error_info = result.get('error', {})
        error_msg = error_info.get('message', 'Unknown error - No choices in response.')
        print(f"API Error (parsed JSON): {error_msg}")
        raise RuntimeError(f"API call successful but response lacks 'choices': {error_msg}")

    raw_output = result["choices"][0]["message"]["content"]
    print(f"Extracted content from choices[0].message.content: '{raw_output}'")

    try:
        extracted_json = extract_json_from_text(raw_output)
        # Basic validation after extraction
        if not all(k in extracted_json for k in ["location", "date_from", "date_to", "granularity"]):
             raise ValueError("Extracted JSON is missing required keys.")
        # Ensure granularity is an integer
        if "granularity" in extracted_json and extracted_json["granularity"] is not None:
            try:
                extracted_json["granularity"] = int(extracted_json["granularity"])
            except (ValueError, TypeError):
                 print(f"Warning: Granularity '{extracted_json['granularity']}' is not an integer. Defaulting to 60.")
                 extracted_json["granularity"] = 60
        elif extracted_json.get("granularity") is None:
             print("Warning: Granularity is null in response. Defaulting to 60.")
             extracted_json["granularity"] = 60

        return extracted_json
    except ValueError as e:
        print(f"Error processing LLM output content: {e}")
        raise

def build_openmeteo_json(query: str, api_counts: dict) -> dict:
    print(f"\nStep 1: Transforming query to base JSON via LLM...")
    base_json = transform_query_to_json(query, api_counts)
    print(f"LLM Result (JSON): {json.dumps(base_json)}")

    location = base_json.get("location")
    if not location:
        raise ValueError("LLM did not return a valid location.")

    print(f"\nStep 2: Calling 'get_coordinates' tool for location: {location}")
    try:
        lat, lon = get_coordinates(location, api_counts)
        print(f"Coordinates found: Lat={lat}, Lon={lon}")
    except ValueError as e:
        print(f"Error getting coordinates: {e}")
        raise

    base_json["latitude"] = lat
    base_json["longitude"] = lon

    print("\nStep 3: Final JSON prepared for weather data fetching.")
    return base_json

def build_base_params(lat: float, lon: float, start_date: date, end_date: date) -> dict:
    return {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "auto"
    }

def get_past_params(lat: float, lon: float, start_date: date, end_date: date, requested_granularity: int) -> dict:
    params = build_base_params(lat, lon, start_date, end_date)
    if requested_granularity >= 1440:
        print(f"  Archive API: Requesting DAILY data (user requested >= 1440 min granularity)")
        params["daily"] = "temperature_2m_mean,precipitation_sum,wind_speed_10m_max"
    else:
        print(f"  Archive API: Requesting HOURLY data (user requested {requested_granularity} min granularity)")
        params["hourly"] = "temperature_2m,precipitation,wind_speed_10m"
    return params

def get_forecast_params(lat: float, lon: float, start_date: date, end_date: date, requested_granularity: int) -> dict:
    params = build_base_params(lat, lon, start_date, end_date)
    if requested_granularity < 30:
        print(f"  Forecast API: Requesting MINUTELY_15 data (user requested {requested_granularity} min granularity)")
        params["minutely_15"] = "temperature_2m,precipitation"
    elif requested_granularity >= 1440:
        print(f"  Forecast API: Requesting DAILY data (user requested >= 1440 min granularity)")
        params["daily"] = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,uv_index_max"
    else:
        print(f"  Forecast API: Requesting HOURLY data (user requested {requested_granularity} min granularity)")
        params["hourly"] = "temperature_2m,precipitation_probability,wind_speed_10m,uv_index"
    return params


def fetch_weather_data(lat: float, lon: float, date_from: str, date_to: str, requested_granularity: int, api_counts: dict) -> dict:
    today = date.today()
    try:
        start = datetime.strptime(date_from, "%Y-%m-%d").date()
        end = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format: {e}") from e

    if start > end:
        raise ValueError(f"Start date ({start}) cannot be after end date ({end}).")

    combined_result = {
        "query_details": {
             "latitude": lat,
             "longitude": lon,
             "date_from": date_from,
             "date_to": date_to,
             "requested_granularity_minutes": requested_granularity,
             "fetched_resolution": None,
             "request_time_utc": datetime.utcnow().isoformat() + "Z"
        },
        "past": None,
        "forecast": None
    }
    api_errors = []
    fetched_resolution = []

    print(f"\nStep 4: Fetching weather data (User requested {requested_granularity} min granularity)...")

    if start < today:
        past_to = min(end, today - timedelta(days=1))
        if past_to >= start:
            print(f"  Fetching past data from {start} to {past_to}...")
            past_url = "https://archive-api.open-meteo.com/v1/archive"
            past_params = get_past_params(lat, lon, start, past_to, requested_granularity)
            api_call_resolution = "daily" if "daily" in past_params else "hourly"
            try:
                api_counts["meteo_archive"] += 1
                print(f"    [API Call] Incrementing Open-Meteo Archive count to: {api_counts['meteo_archive']} (Requesting {api_call_resolution})")
                past_response = requests.get(past_url, params=past_params, timeout=30)
                past_response.raise_for_status()
                combined_result["past"] = past_response.json()
                if api_call_resolution not in fetched_resolution: fetched_resolution.append(api_call_resolution)
                print(f"    Past data ({api_call_resolution}) fetched successfully.")
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to fetch past weather data: {e}"
                print(f"    Error: {error_msg}")
                api_errors.append({"api": "archive", "error": str(e), "params": past_params})

    if end >= today:
        future_from = max(start, today)
        if end >= future_from:
            print(f"  Fetching forecast data from {future_from} to {end}...")
            forecast_url = "https://api.open-meteo.com/v1/forecast"
            forecast_params = get_forecast_params(lat, lon, future_from, end, requested_granularity)
            api_call_resolution = "daily" if "daily" in forecast_params else ("minutely_15" if "minutely_15" in forecast_params else "hourly")
            try:
                api_counts["meteo_forecast"] += 1
                print(f"    [API Call] Incrementing Open-Meteo Forecast count to: {api_counts['meteo_forecast']} (Requesting {api_call_resolution})")
                forecast_response = requests.get(forecast_url, params=forecast_params, timeout=30)
                forecast_response.raise_for_status()
                combined_result["forecast"] = forecast_response.json()
                if api_call_resolution not in fetched_resolution: fetched_resolution.append(api_call_resolution)
                print(f"    Forecast data ({api_call_resolution}) fetched successfully.")
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to fetch forecast weather data: {e}"
                print(f"    Error: {error_msg}")
                api_errors.append({"api": "forecast", "error": str(e), "params": forecast_params})
        else:
             print(f"  Skipping forecast data fetch (end date {end} is before effective start date {future_from}).")

    combined_result["query_details"]["fetched_resolution"] = ", ".join(fetched_resolution) if fetched_resolution else "None"

    if api_errors:
         combined_result["api_errors"] = api_errors

    if combined_result["past"] is None and combined_result["forecast"] is None and not api_errors:
         print("Warning: No date range specified for past or future, or calls failed without error reports.")
    elif combined_result["past"] is None and combined_result["forecast"] is None and api_errors:
         print("Error: Both past and forecast API calls failed or were not applicable.")

    print("Step 5: Weather data fetching complete.")
    return combined_result

def filter_hourly_data(hourly_data: dict, requested_granularity_minutes: int) -> dict:
    if not hourly_data or 'time' not in hourly_data:
        return hourly_data

    if requested_granularity_minutes <= 60 or requested_granularity_minutes % 1440 == 0:
        return hourly_data

    print(f"  Filtering hourly data to {requested_granularity_minutes} min interval...")
    original_times = hourly_data['time']
    num_points = len(original_times)
    if num_points == 0:
        return hourly_data

    filtered_indices = []
    interval_delta = timedelta(minutes=requested_granularity_minutes)
    try:
        first_timestamp_str = original_times[0].replace("Z", "+00:00")
        first_timestamp = datetime.fromisoformat(first_timestamp_str)
        next_target_time = first_timestamp
    except ValueError as e:
        print(f"    Warning: Could not parse first timestamp '{original_times[0]}': {e}. Skipping filtering.")
        return hourly_data

    for i in range(num_points):
        try:
            current_timestamp_str = original_times[i].replace("Z", "+00:00")
            current_timestamp = datetime.fromisoformat(current_timestamp_str)

            if current_timestamp >= next_target_time:
                filtered_indices.append(i)
                next_target_time = current_timestamp + interval_delta

        except ValueError:
             print(f"    Warning: Could not parse timestamp '{original_times[i]}'. Skipping index {i}.")
             continue

    if not filtered_indices:
        print("    Warning: Filtering resulted in zero data points.")
        filtered_data = {'time': []}
        for key in hourly_data:
            if key != 'time':
                filtered_data[key] = []
        return filtered_data

    filtered_data = {}
    for key, values in hourly_data.items():
        if isinstance(values, list) and len(values) == num_points:
            filtered_data[key] = [values[i] for i in filtered_indices]
        else:
             filtered_data[key] = values

    print(f"  Filtering complete. Reduced points from {num_points} to {len(filtered_indices)}.")
    return filtered_data


def filter_data_by_granularity(weather_data: dict, requested_granularity_minutes: int) -> dict:
    print(f"\nStep 6: Applying filtering based on requested granularity ({requested_granularity_minutes} min)...")

    if not weather_data:
        print("  No weather data to filter.")
        return weather_data

    if weather_data.get("past") and weather_data["past"].get("hourly"):
        print("  Filtering past hourly data...")
        weather_data["past"]["hourly"] = filter_hourly_data(
            weather_data["past"]["hourly"],
            requested_granularity_minutes
        )
    elif weather_data.get("past") and weather_data["past"].get("daily") and requested_granularity_minutes < 1440:
         print("  Warning: Daily past data was fetched, but requested granularity was finer. Cannot filter daily data to hourly/sub-hourly.")
    elif weather_data.get("past"):
         print("  No hourly past data found to filter.")

    if weather_data.get("forecast") and weather_data["forecast"].get("hourly"):
        print("  Filtering forecast hourly data...")
        weather_data["forecast"]["hourly"] = filter_hourly_data(
            weather_data["forecast"]["hourly"],
            requested_granularity_minutes
        )
    elif weather_data.get("forecast") and weather_data["forecast"].get("daily") and requested_granularity_minutes < 1440:
        print("  Warning: Daily forecast data was fetched, but requested granularity was finer. Cannot filter daily data to hourly/sub-hourly.")
    elif weather_data.get("forecast") and weather_data["forecast"].get("minutely_15") and requested_granularity_minutes > 15:
         print(f"  Note: Minutely_15 forecast data was fetched. Filtering to {requested_granularity_minutes} min is not yet implemented, returning raw minutely_15 data.")
         pass
    elif weather_data.get("forecast"):
         print("  No hourly forecast data found to filter.")

    print("Step 7: Filtering complete.")
    return weather_data

def print_weather_summary(weather_data):
    print("\n--- Weather Summary (Placeholder) ---")
    if weather_data.get("past"):
        print("Past Data Available.")
    if weather_data.get("forecast"):
        print("Forecast Data Available.")
    if weather_data.get("api_errors"):
         print(f"API Errors Encountered: {len(weather_data['api_errors'])}")