import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime, date

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize the FastMCP server for the "weather" service.
mcp = FastMCP("weather")

# API base URLs
FORECAST_API_BASE = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_FORECAST_API_BASE = "https://historical-forecast-api.open-meteo.com/v1/forecast"
HISTORY_API_BASE = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "auto"

async def fetch_data(url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error while fetching data: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logging.error(f"Unexpected error while fetching data: {e}")
        return None

@mcp.tool()
async def get_forecast(latitude: float, longitude: float, granularity: int, request_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve forecast or historical forecast weather data for the specified variables.

    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        granularity: Temporal granularity in minutes (60 = hourly, 1440 = daily).
        request_date: Optional ISO date string (YYYY-MM-DD). If in the past, historical forecast is used.

    Returns:
        A JSON object with the forecast or historical forecast data.
    """
    today = date.today()
    use_historical_forecast = False

    if request_date:
        try:
            requested = datetime.strptime(request_date, "%Y-%m-%d").date()
            if requested < today:
                use_historical_forecast = True
        except ValueError:
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": TIMEZONE,
    }

    if granularity < 1440:
        params["hourly"] = (
            "shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,"
            "global_tilted_irradiance,terrestrial_radiation,"
            "diffuse_radiation_instant,direct_normal_irradiance_instant,global_tilted_irradiance_instant,"
            "terrestrial_radiation_instant,temperature_2m"
        )
    else:
        params["daily"] = (
            "temperature_2m_mean,sunrise,sunset,daylight_duration,sunshine_duration,"
            "uv_index_max,shortwave_radiation_sum"
        )

    if use_historical_forecast and request_date:
        params["start_date"] = request_date
        params["end_date"] = request_date
        url = HISTORICAL_FORECAST_API_BASE
    else:
        url = FORECAST_API_BASE

    data = await fetch_data(url, params)
    if data is None:
        return {"status": "error", "message": "Unable to fetch data."}

    return {"status": "success", "data": data}

@mcp.tool()
async def get_history(latitude: float, longitude: float, start_date: str, end_date: str, granularity: int) -> Dict[str, Any]:
    """
    Retrieve historical weather data for the specified variables.

    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        start_date: History start date in "YYYY-MM-DD" format.
        end_date: History end date in "YYYY-MM-DD" format.
        granularity: Temporal granularity in minutes (e.g., 60 for hourly data, 1440 for daily data)

    Returns:
        A JSON object with the historical weather data.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": TIMEZONE
    }

    if granularity < 1440:
        params["hourly"] = (
            "shortwave_radiation,direct_radiation,diffuse_radiation,direct_normal_irradiance,"
            "global_tilted_irradiance,terrestrial_radiation,"
            "diffuse_radiation_instant,direct_normal_irradiance_instant,global_tilted_irradiance_instant,"
            "terrestrial_radiation_instant,temperature_2m"
        )
    else:
        params["daily"] = (
            "temperature_2m_mean,sunrise,sunset,daylight_duration,sunshine_duration"
        )

    data = await fetch_data(HISTORY_API_BASE, params)
    if data is None:
        return {"status": "error", "message": "Unable to fetch historical data."}

    return {"status": "success", "data": data}

if __name__ == "__main__":
    # Run the MCP server using stdio transport.
    mcp.run(transport="stdio")

