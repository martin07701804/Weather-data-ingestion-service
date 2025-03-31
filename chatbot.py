import os
import json
import re
import requests
from dotenv import load_dotenv
from geo import get_coordinates
from prompts import weather_prompt
from os import getenv

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
    raw_output = result["choices"][0]["message"]["content"]

    return extract_json_from_text(raw_output)


def build_openmeteo_json(query: str) -> dict:
    base_json = transform_query_to_json(query)
    location = base_json.get("location")
    lat, lon = get_coordinates(location)
    base_json["latitude"] = lat
    base_json["longitude"] = lon
    return base_json
