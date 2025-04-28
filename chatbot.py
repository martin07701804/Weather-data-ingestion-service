
import os
import json
import re
import requests
import time
from dotenv import load_dotenv
from geo import get_coordinates
from prompts import SYSTEM_PROMPT, ROLE_SYSTEM, ROLE_USER, weather_user_prompt
from os import getenv
from datetime import date, datetime, timedelta

load_dotenv()

API_KEY = getenv("OPENROUTER_API_KEY")
API_URL = getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = getenv("OPENROUTER_MODEL", "deepseek/deepseek-v3-base:free")


DAILY_SOLAR_FORECAST = "sunrise,sunset,uv_index_max,daylight_duration"
DAILY_SOLAR_PAST = "sunrise,sunset,daylight_duration" #no UV for hitorical data

# Max retries for LLM call
LLM_MAX_RETRIES = 2
LLM_RETRY_DELAY_SECONDS = 2


def extract_json_from_text(text: str) -> dict:
    """
    Extracts the first valid JSON object matching the expected weather structure.
    Prioritizes ```json ... ``` blocks, then looks for the first parsable {...}.
    """
    # 1. Prioritize ```json ``` blocks
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            parsed = json.loads(json_str)
            # Check if the parsed JSON from the block has the required keys
            if all(k in parsed for k in ["location", "date_from", "date_to", "granularity"]):
                print("Found valid JSON inside ```json ... ``` block.")
                return parsed
            else:
                 print("Warning: Found ```json ... ``` block, but content missing required keys. Continuing search.")
        except json.JSONDecodeError as e:
            print(f"Warning: Found ```json block, but failed to parse: {e}. Continuing search.")

    # 2. If no valid ```json``` block found, search for the first plausible {...} block
    print("No valid ```json ... ``` block found or parsed. Searching for first general {...} block.")
    first_brace = text.find('{')
    if first_brace == -1:
        raise ValueError("No opening brace '{' found in model response.")

    # Try to find the matching closing brace for the *first* opening brace
    brace_level = 0
    end_brace_index = -1
    for i in range(first_brace, len(text)):
        char = text[i]
        if char == '{':
            brace_level += 1
        elif char == '}':
            if brace_level > 0:
                brace_level -= 1
                if brace_level == 0:
                    end_brace_index = i
                    break # Found the matching closing brace

    if end_brace_index != -1:
        potential_json_str = text[first_brace : end_brace_index + 1]
        try:
            parsed = json.loads(potential_json_str)
            # Check if this first block has the required keys
            if all(k in parsed for k in ["location", "date_from", "date_to", "granularity"]):
                 print(f"Found first plausible {{...}} block and parsed successfully.")
                 return parsed
            else:
                 print("Warning: Parsed first {...} block, but content missing required keys.")
                 # Fall through to raise error later if this was the only chance
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse the first {{...}} block: {e}")
            # Fall through to raise error later if this was the only chance
    else:
        print("Warning: Could not find matching closing brace '}' for the first opening brace.")


    # 3. If neither method worked, raise an error
    raise ValueError("No valid JSON object matching expected structure found in model response (checked ```json``` and first {...}).")

def transform_query_to_json(query: str, api_counts: dict) -> dict:
    user_message_content = weather_user_prompt.format(query=query)

    # Get today's date and format the system prompt
    today_str = date.today().isoformat()
    try:
        formatted_system_prompt = SYSTEM_PROMPT.format(current_date=today_str)
    except KeyError as e:
         print(f"ERROR: Issue formatting system prompt. Check placeholders. Error: {e}")
         # Fallback to original prompt if formatting fails
         formatted_system_prompt = SYSTEM_PROMPT.replace("{current_date}", today_str)


    messages = [
        {"role": ROLE_SYSTEM, "content": formatted_system_prompt},
        {"role": ROLE_USER, "content": user_message_content}
    ]

    print(f"--- Sending to LLM ({MODEL}) ---")
    print(f"User Query (for LLM): {query}")
    print(f"System Prompt Context: Includes current date {today_str}")
    print("-" * 20)

    last_error = None

    for attempt in range(LLM_MAX_RETRIES + 1):
        print(f"  LLM Call Attempt {attempt + 1}/{LLM_MAX_RETRIES + 1}")
        if attempt > 0:
            print(f"  Waiting {LLM_RETRY_DELAY_SECONDS}s before retrying...")
            time.sleep(LLM_RETRY_DELAY_SECONDS)
            api_counts["llm"] += 1
            print(f"  [API Call] Incrementing LLM count to: {api_counts['llm']}")


        raw_response_text = None
        response_status_code = None
        extracted_json = None
        raw_output = None

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

            print(f"--- LLM API Response (Attempt {attempt + 1}) ---")
            print(f"Status Code: {response_status_code}")
            # Limit printing very long raw bodies if needed
            print(f"Raw Body Text:\n<<<\n{raw_response_text[:1000]}{'...' if len(raw_response_text) > 1000 else ''}\n>>>")
            print("-" * 20)

            response.raise_for_status() # Check for HTTP errors first

            result = response.json()

            if "choices" not in result or not result["choices"] or "message" not in result["choices"][0]:
                error_info = result.get('error', {})
                error_msg = error_info.get('message', 'API OK but response lacks choices/message structure.')
                print(f"API Error (parsed JSON): {error_msg}")
                last_error = RuntimeError(f"API call successful but response structure invalid: {error_msg}")
                continue # Go to next retry attempt

            raw_output = result["choices"][0]["message"].get("content")

            if not raw_output or raw_output.isspace():
                 print(f"Warning: LLM returned empty or whitespace content.")
                 last_error = ValueError("LLM returned empty content.")
                 continue # Go to next retry attempt

            print(f"Extracted content from choices[0].message.content: '{raw_output[:100]}...'") # Limit print length

            # Try extracting JSON
            extracted_json = extract_json_from_text(raw_output)

            # Basic validation after extraction
            if not all(k in extracted_json for k in ["location", "date_from", "date_to", "granularity"]):
                 print(f"Warning: Extracted JSON is missing required keys.")
                 last_error = ValueError("Extracted JSON is missing required keys.")


            # Ensure granularity is an integer
            if "granularity" in extracted_json:
                 granularity_val = extracted_json["granularity"]
                 if granularity_val is None:
                     print("Warning: Granularity is null in response. Defaulting to 60.")
                     extracted_json["granularity"] = 60
                 else:
                     try:
                         extracted_json["granularity"] = int(granularity_val)
                     except (ValueError, TypeError):
                         print(f"Warning: Granularity '{granularity_val}' is not an integer. Defaulting to 60.")
                         extracted_json["granularity"] = 60

            # If we got valid JSON, break the loop
            print("Successfully extracted valid JSON.")
            break

        except requests.exceptions.RequestException as e:
            print(f"Error calling LLM API (Attempt {attempt + 1}): {e}")
            last_error = RuntimeError(f"API call failed: {e}")
            # Continue to retry on network/request errors

        except json.JSONDecodeError as e:
            print(f"Error: API returned status {response_status_code} but body is not valid JSON (Attempt {attempt + 1}).")
            print(f"JSONDecodeError: {e}")
            last_error = RuntimeError(f"API response was not valid JSON (status {response_status_code})")
             # Continue to retry

        except ValueError as e: # Catch JSON extraction errors
            print(f"Error processing LLM output content (Attempt {attempt + 1}): {e}")
            print(f"Raw output was: '{raw_output}'")
            last_error = e
            # Continue to retry if JSON structure is wrong

        except Exception as e: # Catch unexpected errors
            print(f"An unexpected error occurred during LLM processing (Attempt {attempt + 1}): {e}")
            last_error = e
            # Potentially break or continue depending on error type
            break # Break on truly unexpected errors


    # After the loop, check if we succeeded
    if extracted_json:
        return extracted_json
    else:
        print(f"LLM call failed after {LLM_MAX_RETRIES + 1} attempts.")
        # Raise the last error encountered, or a generic error if None
        final_error = last_error or RuntimeError("LLM failed to produce valid JSON after multiple retries.")
        raise final_error



def build_openmeteo_json(query: str, api_counts: dict) -> dict:
    print(f"\nStep 1: Transforming query to base JSON via LLM...")
    base_json = transform_query_to_json(query, api_counts)
    print(f"LLM Result (JSON): {json.dumps(base_json)}")

    location = base_json.get("location")
    if not location:
        raise ValueError("LLM did not return a valid location (or JSON processing failed).")

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
def get_past_params(lat: float, lon: float, start_date: date, end_date: date) -> dict:
    print("  Archive API: Requesting maximum granularity (Hourly + Daily)")
    params = build_base_params(lat, lon, start_date, end_date)
    params["hourly"] = "temperature_2m,precipitation,wind_speed_10m"
    params["daily"] = f"temperature_2m_mean,precipitation_sum,wind_speed_10m_max,{DAILY_SOLAR_PAST}"
    return params

def get_forecast_params(lat: float, lon: float,
                        start_date: date, end_date: date) -> dict:
    print("  Forecast API: Requesting appropriate granularity")
    params = build_base_params(lat, lon, start_date, end_date)

    # calc days for meteo API limit
    day_span = (end_date - start_date).days + 1

    if day_span <= 31:
        # wihtin API limit for minutely
        params["minutely_15"] = "temperature_2m,precipitation"
    else:
        # over Meteo API limit - switch to hourly
        print(f"    Notice: date range {day_span} > 31 days → skipping minutely_15.")

    params["hourly"] = (
        "temperature_2m,precipitation_probability,wind_speed_10m,uv_index"
    )
    params["daily"] = (
        f"temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"wind_speed_10m_max,{DAILY_SOLAR_FORECAST}"
    )
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

    fetched_resolution = set()

    print(f"\nStep 4: Fetching weather data (User requested {requested_granularity} min granularity, fetching max available)...")
    # --- History Data Fetch ---
    if start < today:
        past_to = min(end, today - timedelta(days=1))
        if past_to >= start:
            print(f"  Fetching past data from {start} to {past_to}...")
            past_url = "https://archive-api.open-meteo.com/v1/archive"
            # Call the modified function - always gets hourly+daily
            past_params = get_past_params(lat, lon, start, past_to)
            api_call_resolutions = ["hourly", "daily"]
            try:
                api_counts["meteo_archive"] += 1
                print(f"    [API Call] Incrementing Open-Meteo Archive count to: {api_counts['meteo_archive']} (Requesting {', '.join(api_call_resolutions)})")
                past_response = requests.get(past_url, params=past_params, timeout=45)
                past_response.raise_for_status()
                combined_result["past"] = past_response.json()

                if combined_result["past"]:
                     if "hourly" in combined_result["past"]: fetched_resolution.add("hourly")
                     if "daily" in combined_result["past"]: fetched_resolution.add("daily")
                print(f"    Past data ({', '.join(r for r in api_call_resolutions if r in fetched_resolution)}) fetched successfully.")
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to fetch past weather data: {e}"
                print(f"    Error: {error_msg}")
                api_errors.append({"api": "archive", "error": str(e), "params": past_params})
            except json.JSONDecodeError as e:
                error_msg = f"Failed to decode JSON from past weather API: {e}"
                print(f"    Error: {error_msg}")
                api_errors.append({"api": "archive", "error": error_msg, "params": past_params})


    # --- Forecast Data Fetch ---
    if end >= today:
        future_from = max(start, today)
        if end >= future_from:
            print(f"  Fetching forecast data from {future_from} to {end}...")
            forecast_url = "https://api.open-meteo.com/v1/forecast"

            forecast_params = get_forecast_params(lat, lon, future_from, end)
            api_call_resolutions = ["minutely_15", "hourly", "daily"]
            try:
                api_counts["meteo_forecast"] += 1
                print(f"    [API Call] Incrementing Open-Meteo Forecast count to: {api_counts['meteo_forecast']} (Requesting {', '.join(api_call_resolutions)})")
                forecast_response = requests.get(forecast_url, params=forecast_params, timeout=45)
                forecast_response.raise_for_status()
                combined_result["forecast"] = forecast_response.json()

                if combined_result["forecast"]:
                    if "minutely_15" in combined_result["forecast"]: fetched_resolution.add("minutely_15")
                    if "hourly" in combined_result["forecast"]: fetched_resolution.add("hourly")
                    if "daily" in combined_result["forecast"]: fetched_resolution.add("daily")
                print(f"    Forecast data ({', '.join(r for r in api_call_resolutions if r in fetched_resolution)}) fetched successfully.")
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to fetch forecast weather data: {e}"
                print(f"    Error: {error_msg}")
                api_errors.append({"api": "forecast", "error": str(e), "params": forecast_params})
            except json.JSONDecodeError as e:
                error_msg = f"Failed to decode JSON from forecast weather API: {e}"
                print(f"    Error: {error_msg}")
                api_errors.append({"api": "forecast", "error": error_msg, "params": forecast_params})

        else:
             print(f"  Skipping forecast data fetch (end date {end} is before effective start date {future_from}).")


    combined_result["query_details"]["fetched_resolution"] = ", ".join(sorted(list(fetched_resolution))) if fetched_resolution else "None"

    if api_errors:
         combined_result["api_errors"] = api_errors


    if not combined_result.get("past") and not combined_result.get("forecast"):
        if api_errors:
            print("Error: Both past and forecast API calls failed or returned no data.")
        else:

            print("Warning: No data fetched. Check date range or API availability.")


    print("Step 5: Weather data fetching complete (max granularity).")
    return combined_result


def _filter_time_series_data(
    data: dict,
    base_interval_minutes: int,
    requested_granularity_minutes: int,
    level_name: str
    ) -> dict:
    """ Helper function to filter time series data like hourly or minutely. """
    if not data or 'time' not in data or not data['time']:

        return data

    original_times = data['time']
    num_points = len(original_times)

    # No filtering needed if requested granularity is same or finer than base, or daily request
    if requested_granularity_minutes <= base_interval_minutes or requested_granularity_minutes >= 1440:

        return data

    print(f"  Filtering {level_name} data (base {base_interval_minutes} min) down to {requested_granularity_minutes} min interval...")

    filtered_indices = []
    interval_delta = timedelta(minutes=requested_granularity_minutes)

    try:

        first_timestamp_str = original_times[0]
        first_timestamp = datetime.fromisoformat(first_timestamp_str.replace("Z", "+00:00"))
        next_target_time = first_timestamp

    except (ValueError, TypeError) as e:
        print(f"    Warning: Could not parse first timestamp '{original_times[0]}' for filtering {level_name} anchor: {e}. Skipping filtering.")
        return data

    current_target_index = 0

    for i in range(num_points):
        try:
            current_timestamp_str = original_times[i]
            current_timestamp = datetime.fromisoformat(current_timestamp_str.replace("Z", "+00:00"))


            if current_timestamp >= next_target_time:
                filtered_indices.append(i)

                current_target_index += 1
                next_target_time = first_timestamp + (current_target_index * interval_delta)

                # Optimization: If the current point is *way* past the next target,
                # advance the target time further to avoid unnecessary checks later.
                # This helps if there are gaps in the source data.
                while next_target_time <= current_timestamp:
                     current_target_index += 1
                     next_target_time = first_timestamp + (current_target_index * interval_delta)


        except (ValueError, TypeError):
             print(f"    Warning: Could not parse {level_name} timestamp '{original_times[i]}'. Skipping index {i}.")
             continue

    if not filtered_indices:
        print(f"    Warning: Filtering {level_name} resulted in zero data points.")

        filtered_data = {'time': []}
        for key, value in data.items():
            if key != 'time' and isinstance(value, list) and len(value) == num_points:
                 filtered_data[key] = []
            elif key != 'time':
                 filtered_data[key] = value
        return filtered_data


    filtered_data = {}
    for key, values in data.items():

        if isinstance(values, list) and len(values) == num_points:
            try:
                filtered_data[key] = [values[i] for i in filtered_indices]
            except IndexError:
                 print(f"    Warning: IndexError filtering key '{key}' in {level_name} data. Skipping this key.")
                 filtered_data[key] = []
        else:

             filtered_data[key] = values


    return filtered_data


def filter_minutely_data(minutely_data: dict, requested_granularity_minutes: int) -> dict:
    """ Filters 15-minutely data down to the requested granularity. """
    return _filter_time_series_data(minutely_data, 15, requested_granularity_minutes, "minutely_15")

def filter_hourly_data(hourly_data: dict, requested_granularity_minutes: int) -> dict:
    """ Filters hourly data down to the requested granularity. """
    return _filter_time_series_data(hourly_data, 60, requested_granularity_minutes, "hourly")



def filter_data_by_granularity(weather_data: dict, requested_granularity_minutes: int) -> dict:
    """
    Filters the fetched weather data (which has max granularity) down to the
    user's requested granularity and removes finer-grained data levels.
    """
    print(f"\nStep 6: Filtering fetched data down to requested granularity ({requested_granularity_minutes} min)...")

    if not weather_data:
        print("  No weather data to filter.")
        return weather_data

    req_gran = requested_granularity_minutes

    # --- Filter Forecast Data ---
    if weather_data.get("forecast"):
        forecast = weather_data["forecast"]
        f_minutely = forecast.get("minutely_15")
        f_hourly = forecast.get("hourly")
        # Daily is never filtered down



        if req_gran < 60: # User wants sub-hourly
            if f_minutely:

                forecast["minutely_15"] = filter_minutely_data(f_minutely, req_gran)

                if "hourly" in forecast:
                    forecast.pop("hourly", None)
                    print("    Removed forecast.hourly (coarser than requested).")
            elif f_hourly: # Fallback if minutely wasn't available but sub-hourly requested

                 print("    Warning: Requested sub-hourly, but only hourly forecast available. Filtering hourly.")
                 forecast["hourly"] = filter_hourly_data(f_hourly, req_gran) # Filter hourly as best effort
            else:
                 print("    Warning: Requested sub-hourly, but no minutely_15 or hourly forecast data available.")
                 # Remove potentially empty finer levels if they exist structurally
                 forecast.pop("minutely_15", None)
                 forecast.pop("hourly", None)

        elif req_gran < 1440: # User wants hourly or multi-hourly (e.g., 180 min)
             if f_hourly:

                 forecast["hourly"] = filter_hourly_data(f_hourly, req_gran)
                 # Remove minutely data as it's finer than requested
                 if "minutely_15" in forecast:
                      forecast.pop("minutely_15", None)
                      print("    Removed forecast.minutely_15 (finer than requested).")
             else:
                  print("    Warning: Requested hourly granularity, but no hourly forecast data available.")
                  # Remove finer levels if they exist
                  forecast.pop("minutely_15", None)

        else: # User wants daily (req_gran >= 1440)

             # Remove finer levels
            if "minutely_15" in forecast:
                forecast.pop("minutely_15", None)
                print("    Removed forecast.minutely_15 (finer than requested).")
            if "hourly" in forecast:
                forecast.pop("hourly", None)
                print("    Removed forecast.hourly (finer than requested).")

    # --- Filter Past Data ---
    if weather_data.get("past"):
        past = weather_data["past"]
        p_hourly = past.get("hourly")
       # Daily is never filtered down



        # Past data only has hourly and daily from API
        if req_gran < 1440: # User wants hourly or multi-hourly (or sub-hourly, fallback to hourly)
            if p_hourly:

                if req_gran < 60:
                     print("    Warning: Requested sub-hourly, but only hourly past data available. Filtering hourly.")
                past["hourly"] = filter_hourly_data(p_hourly, req_gran)
                # No finer levels (like minutely) to remove in past data
            else:
                 print(f"    Warning: Requested granularity < 1440 min, but no hourly past data available.")

                 past.pop("hourly", None)


        else: # User wants daily (req_gran >= 1440)

             # Remove finer level (hourly)
             if "hourly" in past:
                 past.pop("hourly", None)
                 print("    Removed past.hourly (finer than requested).")


    print("Step 7: Filtering and data level adjustment complete.")
    return weather_data


def print_weather_summary(weather_data):

    print("\n--- Weather Summary (Placeholder) ---")

    if weather_data.get("forecast") and weather_data["forecast"].get("daily"):
        daily_data = weather_data["forecast"]["daily"]
        if "time" in daily_data and daily_data["time"]:
            print(f"Forecast for {daily_data['time'][0]}:")
            if "sunrise" in daily_data and daily_data["sunrise"]:
                print(f"  Sunrise: {daily_data['sunrise'][0]}")
            if "sunset" in daily_data and daily_data["sunset"]:
                print(f"  Sunset: {daily_data['sunset'][0]}")
            if "uv_index_max" in daily_data and daily_data["uv_index_max"]:
                 print(f"  Max UV Index: {daily_data['uv_index_max'][0]}")
            if "daylight_duration" in daily_data and daily_data["daylight_duration"]:
                 duration_sec = daily_data['daylight_duration'][0]
                 hours = int(duration_sec // 3600)
                 minutes = int((duration_sec % 3600) // 60)
                 print(f"  Daylight Duration: {hours}h {minutes}m")


    if weather_data.get("forecast") and weather_data["forecast"].get("hourly"):
        hourly_data = weather_data["forecast"]["hourly"]
        if "time" in hourly_data and hourly_data["time"]:
            print(f"Forecast Hourly data available (filtered to requested granularity):")

            limit = min(3, len(hourly_data["time"]))
            for i in range(limit):
                temp = hourly_data.get("temperature_2m", [None]*limit)[i]
                print(f"  - {hourly_data['time'][i]}: Temp: {temp}")


    if weather_data.get("past"):
         print("Past Data Available (filtered to requested granularity).")


    if weather_data.get("api_errors"):
         print(f"API Errors Encountered: {len(weather_data['api_errors'])}")

