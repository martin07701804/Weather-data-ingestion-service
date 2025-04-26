import pytest
from geo import get_coordinates

# Dummy geolocator
class DummyLoc:
    def __init__(self, lat, lon):
        self.latitude = lat
        self.longitude = lon

class DummyGeo:
    def __init__(self, loc):
        self._loc = loc
    def geocode(self, _):
        return self._loc

def test_get_coordinates_success(monkeypatch):
    dummy = DummyLoc(50.0, 14.0)
    monkeypatch.setattr("geo.Nominatim", lambda user_agent: DummyGeo(dummy))
    lat, lon = get_coordinates("Prague")
    assert lat == 50.0 and lon == 14.0

def test_get_coordinates_fail(monkeypatch):
    monkeypatch.setattr("geo.Nominatim", lambda user_agent: DummyGeo(None))
    with pytest.raises(ValueError):
        get_coordinates("Nowhere")
