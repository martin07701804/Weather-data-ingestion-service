import os
import sys
import io
import contextlib
import runpy
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_e2e_application(monkeypatch):
    import chatbot

    # Stub build_openmeteo_json
    monkeypatch.setattr(
        chatbot,
        "build_openmeteo_json",
        lambda q: {
            "latitude": 12.34,
            "longitude": 56.78,
            "date_from": "2025-06-01",
            "date_to":   "2025-06-01",
            "granularity": 30
        }
    )

    # Stub fetch_weather_data
    dummy_payload = {"hourly": {"time": ["2025-06-01T00:00"], "temperature_2m": [15]}}
    monkeypatch.setattr(
        chatbot,
        "fetch_weather_data",
        lambda lat, lon, df, dt, gran: dummy_payload
    )

    # Stub print_weather_summary if exists
    monkeypatch.setattr(
        chatbot,
        "print_weather_summary",
        lambda *args, **kwargs: None,
        raising=False
    )

    # Capture stdout and run main.py
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        runpy.run_module("main", run_name="__main__")
    output = buf.getvalue()

    # Check the three sections
    assert "==============================" in output
    assert "Query:" in output

    assert "Final JSON for OpenMeteo API call:" in output
    assert "{'latitude': 12.34, 'longitude': 56.78, 'date_from': '2025-06-01', 'date_to': '2025-06-01', 'granularity': 30}" in output

    assert "-- Full Raw Weather Data --" in output
    # Corrected multi-line assertion:
    assert '"temperature_2m": [' in output
    assert '15' in output
