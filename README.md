# Weather-data-ingestion-service (Standalone Version)

## Project Description

This project provides a standalone Python tool that interprets natural language weather queries. It uses a Large Language Model (LLM) via OpenRouter.ai to parse the query into structured parameters, fetches corresponding weather data (forecasts and history) from Open-Meteo APIs, performs geocoding using Nominatim/OpenStreetMap, filters the data to the requested granularity, and outputs the results.

**This version does NOT include the Model Context Protocol (MCP) server components.** It is intended for direct script execution or integration into other Python projects. For the MCP version designed for AI agent integration, please see the `main` branch.

## Key Features

*   Parses natural language weather queries (e.g., "Weather in Prague tomorrow", "History for Berlin last Tuesday hourly").
*   Uses an external LLM (configurable, defaults to OpenRouter.ai free tier) for query understanding.
*   Fetches forecast and historical weather data from Open-Meteo.
*   Performs geocoding (place name to coordinates) using Nominatim/OpenStreetMap.
*   Fetches data at maximum available granularity (minutely/hourly/daily) based on API limits.
*   Filters the fetched data down to the user's requested time granularity.
*   Tracks API calls and estimates costs (using placeholder values in `main.py`).

## Getting Started

### Prerequisites

*   Git
*   Python (3.9+ recommended)

### Installation

1.  **Clone the repository and checkout this branch:**
    ```bash
    git clone https://github.com/martin07701804/Weather-data-ingestion-service.git
    cd Weather-data-ingestion-service
    git checkout no_MCP_version
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Create the virtual environment
    python -m venv .venv

    # Activate on Linux/macOS
    source .venv/bin/activate

    # Activate on Windows (Command Prompt)
    # .venv\Scripts\activate.bat

    # Activate on Windows (PowerShell)
    # .venv\Scripts\Activate.ps1
    ```

3.  **Install dependencies:**
    (Ensure your virtual environment is activated first)
    ```bash
    pip install -r requirements.txt
    ```

### Configuration (`.env` file)

1.  **Edit the `.env` file:**
    *   **REQUIRED:** You **must** provide your OpenRouter API key for the `OPENROUTER_API_KEY` variable. You can get one from [OpenRouter.ai](https://openrouter.ai/).
    *   Optional: You can change the `OPENROUTER_MODEL`, `OPENROUTER_API_URL`, `YOUR_SITE_URL`, and `YOUR_APP_NAME` if needed, otherwise defaults from the code will be used.
2.  **Do NOT commit the `.env` file to Git.** (Ensure `.env` is listed in your `.gitignore` file). The application uses `python-dotenv` to automatically load these variables.

### Running the Project

The `main.py` script demonstrates how to use the core functions (`build_openmeteo_json`, `fetch_weather_data`, `filter_data_by_granularity`).

*   The script will process a predefined list of queries located in `main.py`.
*   For each query, it will print the steps: LLM interaction, geocoding, weather API calls, filtering, and the final resulting weather data (in JSON format).
*   It will also print estimated API call counts and costs (using placeholder cost values defined in `main.py`).

*   **To process your own queries:** Modify the `queries` list within the `main.py` script or adapt the script to take queries from user input or another source.

## Workflow Overview

1.  **Input:** A natural language weather query (e.g., "Weather in London tomorrow").
2.  **LLM Parsing (`chatbot.py`):** The query is sent to the configured LLM (OpenRouter) with specific instructions (in `prompts.py`) to convert it into a JSON object containing location, dates (YYYY-MM-DD), and granularity (minutes).
3.  **Geocoding (`geo.py`):** The location name from the JSON is converted into latitude and longitude coordinates using Nominatim.
4.  **Weather Data Fetching (`chatbot.py`):** Based on the dates and coordinates, the script makes calls to the appropriate Open-Meteo APIs (Archive API for past dates, Forecast API for future dates), requesting the maximum available data resolution (minutely, hourly, daily).
5.  **Filtering (`chatbot.py`):** The fetched data (which might be finer-grained than requested) is filtered down to match the granularity specified by the user/LLM (e.g., if user asked for hourly, minutely data is removed or filtered).
6.  **Output (`main.py`):** The final, filtered weather data is printed as a JSON object. API usage and estimated costs are also displayed.

## Dependency Management

Project dependencies are listed in `requirements.txt`. 
