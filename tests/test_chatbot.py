import pytest
import json
from datetime import date, timedelta

import chatbot


def test_extract_json_from_text_with_backticks():
    text = (
        "Before text ```json {\"location\":\"Prague\",\"date_from\":\"2025-04-01\","
        "\"date_to\":\"2025-04-02\",\"granularity\":60} ``` after text"
    )
    result = chatbot.extract_json_from_text(text)
    assert result == {
        "location": "Prague",
        "date_from": "2025-04-01",
        "date_to": "2025-04-02",
        "granularity": 60,
    }


def test_extract_json_from_text_inline():
    text = (
        "Query: {\"location\":\"Brno\",\"date_from\":\"2025-04-03\","
        "\"date_to\":\"2025-04-04\",\"granularity\":30} end"
    )
    result = chatbot.extract_json_from_text(text)
    assert result == {
        "location": "Brno",
        "date_from": "2025-04-03",
        "date_to": "2025-04-04",
        "granularity": 30,
    }


def test_extract_json_from_text_missing_json():
    with pytest.raises(ValueError):
        chatbot.extract_json_from_text("No JSON here!")


def test_build_base_params():
    p = chatbot.build_base_params(50.0, 14.0, date(2025, 4, 1), date(2025, 4, 2))
    assert p == {
        "latitude": 50.0,
        "longitude": 14.0,
        "start_date": "2025-04-01",
        "end_date": "2025-04-02",
        "timezone": "auto",
    }


def test_get_past_params_fields():
    start = date(2025, 3, 1)
    end = date(2025, 3, 15)
    params = chatbot.get_past_params(10.0, 20.0, start, end)
    # Should include base params plus hourly and daily
    assert params["latitude"] == 10.0
    assert params["longitude"] == 20.0
    assert params["start_date"] == "2025-03-01"
    assert params["end_date"] == "2025-03-15"
    assert "hourly" in params and "daily" in params


def test_get_forecast_params_within_31_days():
    start = date(2025, 4, 1)
    end = date(2025, 4, 10)
    params = chatbot.get_forecast_params(11.0, 21.0, start, end)
    # For 10-day range, should include minutely_15, hourly, and daily
    assert "minutely_15" in params
    assert "hourly" in params
    assert "daily" in params


def test_get_forecast_params_over_31_days():
    start = date(2025, 1, 1)
    end = date(2025, 2, 5)  # 36 days
    params = chatbot.get_forecast_params(12.0, 22.0, start, end)
    # For >31-day, should omit minutely_15
    assert "minutely_15" not in params
    assert "hourly" in params
    assert "daily" in params


def test_filter_hourly_data_granularity():
    # Create sample hourly data at 1-hour intervals
    times = [f"2025-04-01T{h:02d}:00:00Z" for h in range(6)]
    temps = list(range(6))
    hourly_data = {"time": times, "temperature_2m": temps}
    # Request every 2 hours
    filtered = chatbot.filter_hourly_data(hourly_data, 120)
    assert filtered["time"] == [times[0], times[2], times[4]]
    assert filtered["temperature_2m"] == [0, 2, 4]


def test_filter_data_by_granularity_empty():
    wd = {}
    out = chatbot.filter_data_by_granularity(wd, 60)
    assert out == {}


def test_filter_data_by_granularity_no_forecast():
    wd = {"forecast": {}}
    out = chatbot.filter_data_by_granularity(wd, 60)
    assert "forecast" in out and out["forecast"] == {}
