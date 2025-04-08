import os
import json
import re
import requests
from dotenv import load_dotenv
from geo import get_coordinates
from prompts import weather_prompt
from os import getenv
from datetime import date, datetime, timedelta


load_dotenv()

API_KEY = getenv("OPENAI_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v3-base:free"


def extract_json_from_text(text: str) -> dict:

    braces = 0
    start_idx = None

    for i, char in enumerate(text):
        if char == '{':
            if braces == 0:
                start_idx = i
            braces += 1
        elif char == '}':
            braces -= 1
            if braces == 0 and start_idx is not None:
                json_str = text[start_idx:i+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
    raise ValueError("No valid JSON object found in model response.")



def build_base_params(lat: float, lon: float, start_date: date, end_date: date) -> dict:
    return {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "auto"
    }

def get_past_params(lat: float, lon: float, start_date: date, end_date: date, granularity: int) -> dict:
    params = build_base_params(lat, lon, start_date, end_date)
    # If data is needed for a full day or longer intervals, use daily summary (1440 min = 1 day).
    if granularity >= 1440:
        params["daily"] = "temperature_2m_mean"
    elif granularity <= 60:
        params["hourly"] = "temperature_2m"
    elif granularity <= 180:
        params["hourly"] = "temperature_2m"
        params["temporal_resolution"] = "hourly_3"
    elif granularity <= 360:
        params["hourly"] = "temperature_2m"
        params["temporal_resolution"] = "hourly_6"
    else:
        # Fallback: default to hourly for unexpected granularity values
        params["hourly"] = "temperature_2m"
    return params

def get_forecast_params(lat: float, lon: float, start_date: date, end_date: date, granularity: int) -> dict:
    params = build_base_params(lat, lon, start_date, end_date)
    # For very fine resolution (below 30 min), use minutely data if available
    if granularity < 30:
        params["minutely_15"] = "temperature_2m,uv_index"
    elif granularity <= 60:
        params["hourly"] = "temperature_2m,uv_index"
    elif granularity <= 180:
        params["hourly"] = "temperature_2m,uv_index"
        params["temporal_resolution"] = "hourly_3"
    elif granularity <= 360:
        params["hourly"] = "temperature_2m,uv_index"
        params["temporal_resolution"] = "hourly_6"
    else:
        # Fallback: default to hourly if granularity exceeds 360 minutes
        params["hourly"] = "temperature_2m,uv_index"
    return params

def fetch_weather_data(lat: float, lon: float, date_from: str, date_to: str, granularity: int) -> dict:
    # Parse dates from input strings
    today = date.today()
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    combined_result = {}

    # Get past weather data if the start date is before today
    if start < today:
        # For past data, limit the query up to yesterday at most.
        past_to = min(end, today - timedelta(days=1))
        past_url = "https://archive-api.open-meteo.com/v1/archive"
        past_params = get_past_params(lat, lon, start, past_to, granularity)
        past_response = requests.get(past_url, params=past_params)
        past_response.raise_for_status()
        combined_result["past"] = past_response.json()

    # Get forecast weather data if the end date is today or later.
    if end >= today:
        future_from = max(start, today)
        forecast_url = "https://api.open-meteo.com/v1/forecast"
        forecast_params = get_forecast_params(lat, lon, future_from, end, granularity)
        forecast_response = requests.get(forecast_url, params=forecast_params)
        forecast_response.raise_for_status()
        combined_result["forecast"] = forecast_response.json()

    return combined_result

def transform_query_to_json(query: str) -> dict:
    full_prompt = weather_prompt.format(query=query)

    system_prompt = "You are an assistant that converts natural language weather queries into JSON."

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 300
        }
    )

    result = response.json()
    
    print(result)


    if "choices" not in result:
        raise RuntimeError(f"API call failed: {result.get('error', {}).get('message', 'Unknown error')}")

    raw_output = result["choices"][0]["message"]["content"]

    

    return extract_json_from_text(raw_output)


def build_openmeteo_json(query: str) -> dict:
    base_json = transform_query_to_json(query)
    location = base_json.get("location")
    lat, lon = get_coordinates(location)
    base_json["latitude"] = lat
    base_json["longitude"] = lon
    return base_json



