import pytest
import geo


class DummyLocation:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude


class DummyGeolocator:
    def __init__(self, loc=None, exc=None):
        self._loc = loc
        self._exc = exc

    def geocode(self, name, timeout):
        if self._exc:
            raise self._exc
        return self._loc


def _patch_nominatim(monkeypatch, loc=None, exc=None):
    """
    Patch geo.Nominatim to return a DummyGeolocator with given loc or exc.
    """
    def dummy_factory(*args, **kwargs):
        return DummyGeolocator(loc=loc, exc=exc)
    monkeypatch.setattr(geo, "Nominatim", dummy_factory, raising=True)


def test_get_coordinates_success(monkeypatch):
    dummy_loc = DummyLocation(50.0755, 14.4378)
    _patch_nominatim(monkeypatch, loc=dummy_loc)
    api_counts = {"geocoding": 0}
    coords = geo.get_coordinates("Prague", api_counts)
    assert coords == (50.0755, 14.4378)
    assert api_counts["geocoding"] == 1


def test_get_coordinates_not_found(monkeypatch):
    _patch_nominatim(monkeypatch, loc=None)
    api_counts = {"geocoding": 5}
    with pytest.raises(ValueError) as excinfo:
        geo.get_coordinates("Unknown Place", api_counts)
    assert "not found" in str(excinfo.value)
    assert api_counts["geocoding"] == 6


def test_get_coordinates_geocode_exception(monkeypatch):
    some_exc = RuntimeError("Service unavailable")
    _patch_nominatim(monkeypatch, exc=some_exc)
    api_counts = {"geocoding": 2}
    with pytest.raises(ValueError) as excinfo:
        geo.get_coordinates("Anything", api_counts)
    assert "Geocoding failed" in str(excinfo.value)
    assert api_counts["geocoding"] == 3


def test_get_coordinates_missing_api_counts_key(monkeypatch):
    dummy_loc = DummyLocation(1, 2)
    _patch_nominatim(monkeypatch, loc=dummy_loc)
    api_counts = {}
    with pytest.raises(KeyError):
        geo.get_coordinates("Test", api_counts)
