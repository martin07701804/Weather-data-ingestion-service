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
*   An MCP Client capable of communicating with tools via `stdio`. (See "Connecting an MCP Client" below).


Guide of how to use the mcp: https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues


Possible pre-made MCP clients: https://modelcontextprotocol.io/clients
