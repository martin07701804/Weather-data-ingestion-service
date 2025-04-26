import pytest
from meteosource import get_forecast_for_point

# Návratový objekt simulující requests.Response
class DummyResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
    def json(self):
        return self._payload

def test_get_forecast_success(monkeypatch):
    sample = {
        "hourly": {
            "time": ["2025-01-01T00:00"],
            "temperature_2m": [5.0],
            "relativehumidity_2m": [80],
            "dewpoint_2m": [2.0],
            "precipitation": [0.0],
            "windspeed_10m": [3.0],
            "weathercode": [1]
        }
    }
    monkeypatch.setattr("meteosource.requests.get",
                        lambda url, params: DummyResp(200, sample))
    res = get_forecast_for_point(50.0, 14.0)
    assert res["lat"] == 50.0
    assert res["temperature"] == 5.0

def test_get_forecast_http_error(monkeypatch, capsys):
    monkeypatch.setattr("meteosource.requests.get",
                        lambda url, params: DummyResp(500, {}))
    res = get_forecast_for_point(50.0, 14.0)
    captured = capsys.readouterr().out
    assert res is None
    assert "Chyba při získávání dat" in captured
