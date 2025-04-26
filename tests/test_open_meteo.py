import pytest
import numpy as np
import folium
from tabulate import tabulate


from open_meteo import (
    get_forecast_for_point,
    get_forecast_grid,
    create_table,
    create_map,
)

class DummyResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

#
# TESTY get_forecast_for_point()
#
def test_get_forecast_point_success(monkeypatch):
    sample = {
        "hourly": {
            "time": ["2025-01-01T12:00"],
            "temperature_2m": [20.0],
            "relativehumidity_2m": [50],
            "dewpoint_2m": [10.0],
            "precipitation": [0.1],
            "windspeed_10m": [5.0],
            "weathercode": [2],
        }
    }
    monkeypatch.setattr("open_meteo.requests.get",
                        lambda url, params: DummyResp(200, sample))
    out = get_forecast_for_point(50.0, 14.0)

    assert out["lat"] == 50.0
    assert out["lon"] == 14.0
    assert out["time"] == "2025-01-01T12:00"
    assert out["temperature"] == 20.0
    assert out["humidity"] == 50
    assert out["dewpoint"] == 10.0
    assert out["precipitation"] == 0.1
    assert out["windspeed"] == 5.0
    assert out["weathercode"] == 2

def test_get_forecast_point_no_times(monkeypatch):
    # hourly.time je prázdné → vrací None
    monkeypatch.setattr("open_meteo.requests.get",
                        lambda url, params: DummyResp(200, {"hourly": {"time": []}}))
    assert get_forecast_for_point(0, 0) is None

def test_get_forecast_point_http_error(monkeypatch, capsys):
    monkeypatch.setattr("open_meteo.requests.get",
                        lambda url, params: DummyResp(500, {}))
    assert get_forecast_for_point(0, 0) is None
    captured = capsys.readouterr().out
    assert "Chyba při získávání dat" in captured

#
# TEST get_forecast_grid()
#
def test_get_forecast_grid(monkeypatch):
    # Budeme vracet pro každý bod jednoduchý dict
    fake = {"lat": 1, "lon": 2, "time": "t", "temperature": 1, "humidity": 2,
            "dewpoint": 3, "precipitation": 4, "windspeed": 5, "weathercode": 0}
    monkeypatch.setattr("open_meteo.get_forecast_for_point", lambda lat, lon: fake)
    # Aby test neběžel pomalu
    monkeypatch.setattr("open_meteo.time.sleep", lambda s: None)

    grid = get_forecast_grid()
    # Máme 10×10 bodů
    assert isinstance(grid, list)
    assert len(grid) == 100
    assert all(item == fake for item in grid)

#
# TEST create_table()
#
def test_create_table_basic():
    # Vytvoříme dvě záznamy, s různými hodnotami
    data = [
        {"lat":50,"lon":14,"time":"t","temperature":10,"humidity":20,
         "dewpoint":2,"precipitation":0,"windspeed":1,"weathercode":0},
        {"lat":51,"lon":15,"time":"t","temperature":12,"humidity":22,
         "dewpoint":3,"precipitation":0.5,"windspeed":2,"weathercode":1},
    ]
    table_str = create_table(data)
    # Tabulka by měla obsahovat hlavičku i oba řádky a řádek PRŮMĚR
    assert "Latitude" in table_str
    assert "50" in table_str and "51" in table_str
    assert "PRŮMĚR" in table_str

#
# TEST create_map()
#
def test_create_map_minimal():
    points = [
        {"lat":50.0,"lon":14.0,"temperature":5,"humidity":50},
        {"lat":50.1,"lon":14.1,"temperature":6,"humidity":60},
    ]
    m = create_map(points)
    assert isinstance(m, folium.Map)
    # Kontrolujeme, že mapa obsahuje právě 2 markery
    markers = [c for c in m._children.values() if isinstance(c, folium.map.Marker)]
    assert len(markers) == 2
