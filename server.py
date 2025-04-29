import asyncio
import logging
from typing import Any, Dict, Optional, Tuple, Annotated, List
from datetime import datetime, date, timedelta

import httpx
from geopy.geocoders import Nominatim
from geopy.adapters import AioHTTPAdapter
from geopy.extra.rate_limiter import AsyncRateLimiter
from pydantic import BaseModel, ValidationError, Field
from mcp.server.fastmcp import FastMCP

# ----------------------------------------------------------------------------------------------------------------------
# CONFIGURATION & INITIALIZATION
# ----------------------------------------------------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize MCP server under the "weather" namespace
mcp = FastMCP("weather")

# API endpoints
FORECAST_API_BASE = "https://api.open-meteo.com/v1/forecast"
HISTORY_API_BASE = "https://archive-api.open-meteo.com/v1/archive"

# Defaults
TIMEZONE = "auto"
DEFAULT_TIMEOUT = 30.0  
DEFAULT_FORECAST_DAYS = 7
DEFAULT_PAST_DAYS = 0

# Counter for monitoring usage
API_CALLS: Dict[str, int] = {"geocoding": 0, "forecast": 0, "history": 0}

# Reusable HTTP client 
client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)

# ----------------------------------------------------------------------------------------------------------------------
# DATA MODELS & VALIDATION
# ----------------------------------------------------------------------------------------------------------------------

class Coordinate(BaseModel):
    """
    Model: Geographic coordinates validator
    """
    latitude: Annotated[float, Field(ge=-90.0, le=90.0)]
    longitude: Annotated[float, Field(ge=-180.0, le=180.0)]

# ----------------------------------------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------------------------------------------------------

async def fetch_json(
    url: str,
    params: Dict[str, Any],
    count_key: str
) -> Dict[str, Any]:
    """
    Core HTTP GET utility with retry/backoff and API call tracking.
    """
    global client 
    API_CALLS[count_key] += 1
    logger.info(f"Initiating {count_key} API call #{API_CALLS[count_key]} to {url} with params: {params}")
    backoff = 1
    for attempt in range(3):
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            logger.info(f"API call to {url} successful.")
            return resp.json()
        except httpx.TimeoutException as timeout_err:
            logger.warning(f"{count_key} timeout error attempt {attempt+1}: {timeout_err}")
            if attempt == 2: raise
            await asyncio.sleep(backoff)
            backoff *= 2
        except httpx.HTTPStatusError as st_err:
            logger.error(f"{count_key} HTTP status {st_err.response.status_code} for {url}. Response: {st_err.response.text}")
            raise
        except httpx.RequestError as req_err:
            logger.warning(f"{count_key} network error attempt {attempt+1}: {req_err}")
            if attempt == 2: raise
            await asyncio.sleep(backoff)
            backoff *= 2

    # Fallback attempt 
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    logger.info(f"API call to {url} successful on final attempt.")
    return resp.json()


async def get_coordinates(location_name: str) -> Tuple[float, float]:
    """
    Geocode a free-text location using Nominatim (OpenStreetMap) via geopy.
    """
    API_CALLS["geocoding"] += 1
    logger.info(f"Geocoding call #{API_CALLS['geocoding']} for '{location_name}'")
    try:
        async with Nominatim(
            user_agent="openmeteo_mcp_tool",
            adapter_factory=AioHTTPAdapter,
            timeout=15
        ) as geolocator:
            geocode = AsyncRateLimiter(geolocator.geocode, min_delay_seconds=1.1)
            logger.debug(f"Attempting geocode for: {location_name}")
            location = await geocode(location_name, exactly_one=True)
            logger.debug(f"Geocode result for '{location_name}': {location}")
            if location is None:
                logger.warning(f"Geocoding failed: Location '{location_name}' not found.")
                raise ValueError(f"Location '{location_name}' not found.")
            logger.info(f"Geocoding successful for '{location_name}': ({location.latitude}, {location.longitude})")
            return location.latitude, location.longitude
    except Exception as e:
        logger.error(f"Geocoding error for '{location_name}': {e}", exc_info=True)
        raise ValueError(f"Failed to geocode '{location_name}': {e}")

# ----------------------------------------------------------------------------------------------------------------------
# VARIABLE LISTS (from Open-Meteo docs) - Double-check these are correct for your needs
# ----------------------------------------------------------------------------------------------------------------------

DEFAULT_HOURLY_VARS: List[str] = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature",
    "precipitation", "rain", "snowfall", "snow_depth", "weather_code",
    "pressure_msl", "cloud_cover", "shortwave_radiation", "direct_radiation",
    "diffuse_radiation", "uv_index"
]
DEFAULT_DAILY_VARS: List[str] = [
    "weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min",
    "sunrise", "sunset", "daylight_duration", "sunshine_duration",
    "precipitation_sum", "rain_sum", "snowfall_sum", "precipitation_hours",
    "uv_index_max", "wind_speed_10m_max", "wind_gusts_10m_max"
]

# ----------------------------------------------------------------------------------------------------------------------
# MCP TOOLS
# ----------------------------------------------------------------------------------------------------------------------

@mcp.tool()
async def get_forecast(
    place: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    granularity: int = 60,
    forecast_days: Optional[int] = DEFAULT_FORECAST_DAYS,
    past_days: Optional[int] = DEFAULT_PAST_DAYS,
    variables: Optional[str] = None, 
    daily_variables: Optional[str] = None 
) -> Dict[str, Any]:
    """
    **CORE PURPOSE:** Retrieve **future** weather forecasts and weather data for the **very recent past**. Uses the main Open-Meteo real-time forecast API.

    **WHEN TO USE THIS TOOL:**
    - Use for requests about **future** weather: "tomorrow", "next 5 days", "this weekend", "what will the weather be like next week?".
    - Use for requests about the **immediate or very recent past**: "yesterday", "last 2 days", "past 72 hours". Specify the number of days using the `past_days` parameter.
    - Use when the user asks for a forecast spanning *from* the recent past *into* the future (e.g., "last 3 days and next 5 days").

    **WHEN **NOT** TO USE THIS TOOL:**
    - **DO NOT USE** for requests about **specific historical dates or date ranges far in the past** (e.g., "last month", "July 2023", "on January 15th, 2024", "between 2023-01-01 and 2023-01-10").
    - **For any historical data older than roughly 1-3 months, or when a specific past date/range is mentioned, YOU MUST USE the `get_history` tool instead.**

    **PARAMETERS:**
    - `place` OR `latitude`/`longitude`: Specify the location. `place` (e.g., "Prague, CZ") triggers geocoding. If `place` is provided, `latitude`/`longitude` are ignored. One of these location methods is required.
    - `granularity` (Optional[int], Default: 60): Time resolution in minutes.
        - `15`: 15-minute intervals (if available, uses 'minutely_15' variables).
        - `60`: Hourly intervals (default).
        - `>=1440`: Daily summary intervals.
    - `forecast_days` (Optional[int], Default: 7): How many days *into the future* to retrieve (1-16).
    - `past_days` (Optional[int], Default: 0): How many days *into the past* (relative to today) to retrieve (0-~92, exact limit depends on Open-Meteo model). **Crucial for accessing recent history with this tool.**
    - - `variables` (Optional[str]): Comma-separated list of specific **hourly or 15-minutely** weather variable names (e.g., "temperature_2m,precipitation,shortwave_radiation"). 
        If None, default hourly list is used if granularity is 15 or 60.
    - `daily_variables` (Optional[str]): Comma-separated list of specific **daily aggregation** weather variable names (e.g., "temperature_2m_max,precipitation_sum,sunrise,sunset"). 
        If None, default daily list is used if granularity is >= 1440 OR if specific daily vars are needed alongside hourly/minutely data. **Use this to request daily summaries like sunrise/sunset even when getting hourly data.**
    **RETURNS:**
    - Weather data containing predictions for the future period requested (`forecast_days`) and/or observations/analysis for the recent past period requested (`past_days`).
    """



    logger.info(f"Received get_forecast: place='{place}', lat={latitude}, lon={longitude}, "
                f"granularity={granularity}, forecast_days={forecast_days}, past_days={past_days}, "
                f"vars='{variables}', daily_vars='{daily_variables}'") 
    

    if place:
        try:
            latitude, longitude = await get_coordinates(place)
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        if latitude is None or longitude is None:
             return {"status": "error", "message": f"Could not geocode '{place}'."}

    if latitude is None or longitude is None:
        return {"status": "error", "message": "Either 'place' or both 'latitude' and 'longitude' must be provided."}

    try:
        coord = Coordinate(latitude=latitude, longitude=longitude) 
    except ValidationError as e:
        logger.warning(f"Coordinate validation failed: {e.errors()}")
        return {"status": "error", "message": f"Invalid coordinates: {e.errors()}"}

    # --- Prepare API Parameters ---
    params = {
        "latitude": coord.latitude,
        "longitude": coord.longitude,
        "timezone": TIMEZONE, 
    }

    # Handle primary variables based on granularity
    if granularity == 15:
        key = "minutely_15"; default_vars = DEFAULT_HOURLY_VARS 
        params[key] = variables or ",".join(default_vars)
    elif granularity == 60:
        key = "hourly"; default_vars = DEFAULT_HOURLY_VARS
        params[key] = variables or ",".join(default_vars)
    elif granularity >= 1440:
        # If granularity is daily, primary request is daily
        key = "daily"; default_vars = DEFAULT_DAILY_VARS
        # Prioritize explicit daily_variables if provided for daily granularity
        params[key] = daily_variables or variables or ",".join(default_vars)
    else:
        return {"status": "error", "message": f"Unsupported granularity: {granularity}. Use 15, 60, or >=1440."}

    # Add explicitly requested daily variables, regardless of main granularity
    if daily_variables:
         params["daily"] = daily_variables
    # If granularity is daily, ensure the 'daily' key is set (might have been done above)
    elif granularity >= 1440 and "daily" not in params:
         # This handles the case where granularity is daily, but neither 'daily_variables' nor 'variables' were provided
         params["daily"] = ",".join(DEFAULT_DAILY_VARS)

    # Handle forecast_days and past_days
    # Set default forecast days only if neither forecast nor past days are specified.
    add_default_forecast = True
    if forecast_days is not None and forecast_days > 0:
         params["forecast_days"] = min(forecast_days, 16) # API limit is 16
         add_default_forecast = False # User specified forecast days

    if past_days is not None and past_days > 0:
        # Let the API handle the upper limit for past_days as it varies.
        params["past_days"] = past_days
        add_default_forecast = False # User specified past days

    # Add default forecast days if no forecast/past days were specified
    if add_default_forecast:
        params["forecast_days"] = DEFAULT_FORECAST_DAYS

    # --- API Call and Error Handling ---
    url = FORECAST_API_BASE 

    try:
        
        data = await fetch_json(url, params, "forecast")
        logger.info("get_forecast successful.")
        return {"status": "success", "data": data}
    except Exception as err:
        logger.error(f"get_forecast failed for url {url} with params {params}: {err}", exc_info=True)

        # Provide more specific error feedback if possible
        if isinstance(err, httpx.HTTPStatusError) and err.response.status_code == 400:
             api_error_detail = "Could not read API response body."
             guidance = "Check if requested variables (hourly/daily/minutely) are valid for the forecast API and chosen granularity."
             try:
                  
                  api_error_detail = err.response.text
                  error_json = err.response.json()
                  if 'reason' in error_json:
                       guidance += f" API Reason: {error_json['reason']}"
             except Exception:
                  # Ignore if parsing response fails, use raw text if available
                  logger.warning(f"Could not parse JSON error response from API: {api_error_detail}")
                  pass

             return {"status": "error", "message": f"Failed to retrieve forecast due to invalid request (Error 400). {guidance} Raw Response: {api_error_detail}"}

        # Generic error for other exceptions
        return {"status": "error", "message": f"Failed to retrieve forecast: {str(err)}"}



@mcp.tool()
async def get_history(
    place: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,   
    granularity: int = 60,
    variables: Optional[str] = None,
) -> Dict[str, Any]:
    """
    **CORE PURPOSE:** Retrieve **historical** archived weather data for **specific past dates or date ranges**. Uses the dedicated Open-Meteo Archive API.

    **WHEN TO USE THIS TOOL:**
    - Use **whenever** the request asks for weather data for a **specific past date** (e.g., "on January 15th, 2024", "New Year's Day 2023").
    - Use **whenever** the request asks for weather data over a **specific past date range** (e.g., "last month", "July 2023", "the first week of March 2022", "between 2023-01-01 and 2023-01-10").
    - Use for **any historical query older than roughly 1-3 months**, even if a range isn't specified (e.g., "weather back in summer 2022"). You will need to infer appropriate `start_date` and `end_date`.

    **WHEN **NOT** TO USE THIS TOOL:**
    - **DO NOT USE** for requests about **future** weather ("tomorrow", "next week"). Use `get_forecast`.
    - **DO NOT USE** for requests about the **very recent past relative to today** (e.g., "yesterday", "last 3 days") UNLESS a specific date is given. For relative recent past, `get_forecast` with the `past_days` parameter is generally preferred and might use more recent models. However, using `get_history` with calculated dates for the recent past is also acceptable if easier.

    **PARAMETERS:**
    - `place` OR `latitude`/`longitude`: Specify the location. `place` (e.g., "Prague, CZ") triggers geocoding. If `place` is provided, `latitude`/`longitude` are ignored. One of these location methods is required.
    - `start_date` (**Required** [str]): The **start date** for the historical data range in **YYYY-MM-DD format**. This parameter is essential for this tool.
    - `end_date` (**Required** [str]): The **end date** for the historical data range in **YYYY-MM-DD format**. This parameter is essential. Must be the same as or later than `start_date`. For a single day, set `start_date` and `end_date` to the same value.
    - `granularity` (Optional[int], Default: 60): Time resolution in minutes.
        - `60`: Hourly intervals (default).
        - `>=1440`: Daily summary intervals.
        - **Note:** 15-minute data is typically **not available** via the historical archive API. Do not request `granularity=15`.
    - `variables` (Optional[str]): Comma-separated list of specific weather variable names (e.g., "temperature_2m,precipitation_sum,sunshine_duration") to override the defaults. Ensure variables are valid for the chosen granularity and available in the historical archive. If None, default hourly/daily lists are used based on granularity.

    **RETURNS:**
    - Archived historical weather data for the specified location and date range.
    """
    logger.info(f"Received get_history: place='{place}', lat={latitude}, lon={longitude}, "
                f"start={start_date}, end={end_date}, granularity={granularity}")
    

    if place:
        try:
            latitude, longitude = await get_coordinates(place)
        except ValueError as e: return {"status": "error", "message": str(e)}
        if latitude is None or longitude is None: return {"status": "error", "message": f"Could not geocode '{place}'."}

    if latitude is None or longitude is None:
        return {"status": "error", "message": "Either 'place' or both 'latitude' and 'longitude' must be provided."}

    try:
        coord = Coordinate(latitude=latitude, longitude=longitude)
    except ValidationError as e: return {"status": "error", "message": f"Invalid coordinates: {e.errors()}"}

    # ** Check for required dates **
    if not start_date or not end_date:
         return {"status": "error", "message": "The 'start_date' and 'end_date' parameters (in YYYY-MM-DD format) are required for retrieving historical weather data. Please provide the specific past date or date range."}

    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
        if sd > ed: raise ValueError("start_date must be less than or equal to end_date")
    except ValueError as date_err:
        return {"status": "error", "message": f"Invalid date format or range: {date_err}. Use YYYY-MM-DD format for start_date and end_date."}

    if granularity == 60:
        key = "hourly"; param_vars = variables or ",".join(DEFAULT_HOURLY_VARS)
    elif granularity >= 1440:
        key = "daily"; param_vars = variables or ",".join(DEFAULT_DAILY_VARS)
    else: # Explicitly forbid 15 for history
        return {"status": "error", "message": f"Unsupported granularity for history: {granularity}. Use 60 (hourly) or >=1440 (daily). 15-minute data is not available."}

    params = {
        "latitude": coord.latitude, "longitude": coord.longitude,
        "start_date": sd.isoformat(), "end_date": ed.isoformat(),
        "timezone": TIMEZONE, key: param_vars
    }

    try:
        data = await fetch_json(HISTORY_API_BASE, params, "history")
        logger.info("get_history successful.")
        return {"status": "success", "data": data}
    except Exception as err:
        logger.error(f"get_history failed: {err}", exc_info=True)
        # Provide more specific error if possible
        if isinstance(err, httpx.HTTPStatusError) and err.response.status_code == 400:
             return {"status": "error", "message": f"Failed to retrieve history due to invalid request (Error 400). Check if dates are valid and requested variables exist for the chosen granularity in the archive. Detail: {str(err)}"}
        return {"status": "error", "message": f"Failed to retrieve history: {str(err)}"}

# ----------------------------------------------------------------------------------------------------------------------
# MAIN ENTRYPOINT - Simplified
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        logger.info("Starting MCP server...")
        mcp.run(transport="stdio")
        logger.info("MCP server finished running.")

    except KeyboardInterrupt:
        logger.info("Server interrupted by user.")
    except Exception as e:
        # Log any exceptions that occur during server setup or runtime if they bubble up
        logger.exception(f"Server encountered a fatal error: {e}")
    finally:
        logger.info("Initiating HTTP client cleanup...")
        try:
            
            asyncio.run(client.aclose())
            logger.info("HTTP client closed successfully.")
        except Exception as close_err:
            # Log errors during cleanup, but don't crash the exit process
            logger.error(f"Error during HTTP client cleanup: {close_err}", exc_info=True)
