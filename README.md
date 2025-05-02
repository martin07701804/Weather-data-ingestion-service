# Weather-data-ingestion-service

## Project Description

The goal of this project is to provide a service for ingesting weather data, forecasts and actuals, from available sources. The data is processed and formatted to be readily usable in downstream Machine Learning (ML) pipelines or other analytical tasks.

## Key Features

*   Provides weather forecast data (`get_forecast` tool).
*   Provides historical weather data (`get_history` tool).
*   Uses Open-Meteo APIs as the data source.
*   Includes geocoding to convert place names to coordinates (using Nominatim/OpenStreetMap via `geopy`).
*   Designed to be run as a server process communicating via **Standard Input/Output (stdio)** with an MCP client.

## Getting Started

These instructions cover setting up and running the Python **server** component. You will also need an **MCP Client** (like Claude Desktop App, Oppy, etc.) configured to use this server.

### Prerequisites

*   Git
*   Python (3.9+ recommended)
*   An MCP Client capable of communicating with tools via `stdio`. (See "Connecting an MCP Client" below). If you do **not** want to use MCP, please refer to the alternative version mentioned below.

### Alternative (No MCP Version)

If you do not need or want to use the Model Context Protocol (MCP) integration, an alternative version of this project exists without the MCP server components. This version might be suitable for direct scripting or different integration methods.

You can find this version in the `no_MCP_version` branch:
**[https://github.com/martin07701804/Weather-data-ingestion-service/tree/no_MCP_version](https://github.com/martin07701804/Weather-data-ingestion-service/tree/no_MCP_version)**

*(Note: The setup and usage instructions in that branch's README differ from this one.)*

### Installation

1.  **Clone the repository:**
    git clone https://github.com/martin07701804/Weather-data-ingestion-service.git
    cd Weather-data-ingestion-service

2.  **Install dependencies:**
    pip install -r requirements.txt

### Configuration (`.env` file)

Edit the `.env` file with your actual values. **Do not commit the `.env` file to Git.** (Ensure `.env` is listed in your `.gitignore` file). The provided code uses `python-dotenv` which automatically loads variables from this file if it exists.

### Running the Server

This script is designed to run as a persistent server process that communicates over standard input/output (`stdio`).

**Run the main server script:**

    python src/main.py

*   The script will start and wait for JSON-based requests conforming to the Model Context Protocol on its standard input.
*   It will send JSON responses back via its standard output.
*   It will keep running until interrupted (e.g., Ctrl+C) or terminated by the parent process (the MCP client).

### Connecting an MCP Client

  This server **does nothing on its own**. It needs an MCP client to send it tool requests.
  Guide of how to use the mcp: https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues
  Possible pre-made MCP clients: https://modelcontextprotocol.io/clients
  
## Available Tools

*   **`get_forecast`**: Retrieves future weather forecasts and recent past weather data. Requires location (`place` or `latitude`/`longitude`) and accepts parameters for granularity, forecast/past days, and specific variables. See the docstring in the code for detailed usage.
*   **`get_history`**: Retrieves historical archived weather data for specific past dates/ranges. Requires location (`place` or `latitude`/`longitude`), `start_date`, `end_date`, and accepts parameters for granularity and variables. See the docstring in the code for detailed usage.

## Dependency Management

Project dependencies are listed in `requirements.txt`.


