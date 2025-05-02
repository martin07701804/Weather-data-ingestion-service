# Weather-data-ingestion-service  



## Table of Contents
1. [Project Description](#project-description)  
2. [Key Features](#key-features)  
3. [Getting started](#getting-started)  
4. [Installation](#installation)   
5. [Run the Server](#run-the-server)  
6. [Available Tools](#available-tools)  




## Project Description

The goal of this project is to provide a service for ingesting weather data, forecasts and actuals, from available sources. The data is processed and formatted to be readily usable in downstream Machine Learning (ML) pipelines or other analytical tasks.

## Key Features

*   Provides weather forecast data (`get_forecast` tool).
*   Provides historical weather data (`get_history` tool).
*   Uses Open-Meteo APIs as the data source.
*   Includes geocoding to convert place names to coordinates (using Nominatim/OpenStreetMap via `geopy`).
*   Designed to be run as a server process communicating via **Standard Input/Output (stdio)** with an MCP client.

## Getting Started

These instructions cover setting up and running the Python **server** component. You will also need an **MCP Client** (like Claude Desktop App, Oppy, etc.) configured to use this server. In this case we will use Claude Desktop as a client.

More MCP clients:
https://modelcontextprotocol.io/clients

How to create a custom client: 
https://modelcontextprotocol.io/quickstart/client

### Prerequisites

*   Git
*   Python (3.9+ recommended)
*   An MCP Client capable of communicating with tools via `stdio`. (See "Connecting an MCP Client" below). If you do **not** want to use MCP, please refer to the alternative version mentioned below.

### Alternative (No MCP Version)

If you do not need or want to use the Model Context Protocol (MCP) integration, an alternative version of this project exists without the MCP server components. This version might be suitable for direct scripting or different integration methods.

You can find this version in the `no_MCP_version` branch:
**[https://github.com/martin07701804/Weather-data-ingestion-service/tree/no_MCP_version](https://github.com/martin07701804/Weather-data-ingestion-service/tree/no_MCP_version)**

*(Note: The setup and usage instructions in that branch's README differ from this one.)*

## Installation

1.  **Clone the repository:**
   ```bash
    git clone https://github.com/martin07701804/Weather-data-ingestion-service.git
    cd Weather-data-ingestion-service
   ```

3.  **Install uv (recomendation):**
   ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
5. **Create a virtual enviroment and activate it:**
   ```bash
    uv venv
    .venv\Scripts\activate
   ```
   Make sure a pyproject.toml file has been created.


7. **Install dependencies:**
   ```bash
   uv add -r requirements.txt
   ```

### Claude Desktop configuration (or other client)

1. **Install Claude Desktop:**
   
   Here: https://claude.ai/download
   
3. **Activate developer tools and go to settings:**
   
   On the upper left menu.

   
   ![image](https://github.com/user-attachments/assets/05e5c5e3-7f48-4c0e-b119-3b188c4d517b)
   ![image](https://github.com/user-attachments/assets/62a813ee-d9e5-4c9a-b2c2-b2e8ea40295f)

5. **Create and edit config file:**
   Click on edit config to create it on `Windows: %APPDATA%\Claude\claude_desktop_config.json`
   
   Replace the content with this:
```JSON
    {
      "mcpServers": {
        "weather": {
          "command": "uv",
          "args": [
            "run",
            "--with",
            "mcp[cli]",
            "mcp",
            "run",
            "ABSOLUTE_PATH_TO_server.py"
          ]
        }
      }
    }
```
   Or use the command:
   ```bash
   mcp install server.py
   ```
## Run the server

This script is designed to run as a persistent server process that communicates over standard input/output (`stdio`).

1. **Use the command:**
   ```bash
   uv run server.py
   ```

   Expected output:

   `2025-05-02 12:51:59,150 [INFO] __main__: Starting MCP server...`

3. **Restart Claude Desktop if neccesary.**
   You may have to open it as an administrator
4. **Verify startup:**
   Now this icon must appear on Claude Desktop:
   
   ![image](https://github.com/user-attachments/assets/c7ac546a-65ca-4b3c-95ee-05430ceae3d6)




    


### Configurate `.env` file if you need to use an Open Meteo or Geopy API key

Rigth now the code only works with the free API usage for both services.




## Available Tools

*   **`get_forecast`**: Retrieves future weather forecasts and recent past weather data. Requires location (`place` or `latitude`/`longitude`) and accepts parameters for granularity, forecast/past days, and specific variables. See the docstring in the code for detailed usage.
*   **`get_history`**: Retrieves historical archived weather data for specific past dates/ranges. Requires location (`place` or `latitude`/`longitude`), `start_date`, `end_date`, and accepts parameters for granularity and variables. See the docstring in the code for detailed usage.

## Dependency Management

Project dependencies are listed in `requirements.txt`.


