import pytest


import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from geo import get_coordinates

# --- Helpers --------------------------------------------------------------

class DummyLoc:
    """Simulates a geopy Location with latitude and longitude attributes."""
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

class DummyGeo:
    """Simulates a geocoder where geocode() returns either a DummyLoc or None."""
    def __init__(self, loc):
        self._loc = loc

    def geocode(self, name):
        # ignore 'name'—always return the preset location
        return self._loc

# --- Tests ---------------------------------------------------------------

def test_get_coordinates_success(monkeypatch):
    """
    Should return (latitude, longitude) for a valid location.
    """
    dummy = DummyLoc(50.0, 14.0)
    # Replace Nominatim so that geolocator.geocode(...) returns our dummy
    monkeypatch.setattr("geo.Nominatim", lambda user_agent: DummyGeo(dummy))

    lat, lon = get_coordinates("Prague")
    assert lat == 50.0 and lon == 14.0

def test_get_coordinates_not_found(monkeypatch):
    """
    Should raise ValueError if the location is not found.
    We monkeypatch Nominatim to return None.
    """
    monkeypatch.setattr("geo.Nominatim", lambda user_agent: DummyGeo(None))

    with pytest.raises(ValueError) as excinfo:
        get_coordinates("NowhereLand")


    assert "Location 'NowhereLand' not found." in str(excinfo.value)
