import os
import sys
import io
import contextlib
import runpy
import pytest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_main_script_outputs(monkeypatch):
    """
    Verify that running main.py as a script:
    - Imports without error (including print_weather_summary)
    - Prints the query header
    - Prints the final JSON returned by build_openmeteo_json
    - Prints the raw weather data JSON
    We stub out build_openmeteo_json, fetch_weather_data and print_weather_summary.
    """
    # Stub chatbot module functions/attributes
    import chatbot

    # Stub build_openmeteo_json
    monkeypatch.setattr(
        chatbot, "build_openmeteo_json",
        lambda q: {
            "latitude": 50,
            "longitude": 14,
            "date_from": "2025-04-09",
            "date_to":   "2025-04-09",
            "granularity": 120
        }
    )

    # Stub fetch_weather_data
    dummy_data = {"weather": ["sunny", "cloudy"]}
    monkeypatch.setattr(
        chatbot, "fetch_weather_data",
        lambda lat, lon, df, dt, gran: dummy_data
    )

    # Stub print_weather_summary (allows new attribute)
    monkeypatch.setattr(
        chatbot, "print_weather_summary",
        lambda *args, **kwargs: None,
        raising=False
    )

    # Capture stdout while executing main.py under __main__
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        runpy.run_module("main", run_name="__main__")
    output = buf.getvalue()

    # Assertions on printed output
    assert "==============================" in output
    assert "Query: What's the weather in Berlin in the 2025/04/09 measured every 2 hours?" in output

    assert "Final JSON for OpenMeteo API call:" in output
    assert "{'latitude': 50, 'longitude': 14, 'date_from': '2025-04-09', 'date_to': '2025-04-09', 'granularity': 120}" in output

    assert "-- Full Raw Weather Data --" in output
    assert '"weather": [' in output
    assert '"sunny"' in output and '"cloudy"' in output
