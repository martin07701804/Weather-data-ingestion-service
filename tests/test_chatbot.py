import json
import pytest

from chatbot import extract_json_from_text, transform_query_to_json, build_openmeteo_json

# Dummy response pro requests.post
class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
    def json(self):
        return self._payload

def test_extract_json_simple():
    text = 'Some text {"key":"value"} trailing'
    assert extract_json_from_text(text) == {"key": "value"}

def test_extract_json_nested():
    text = 'X {"outer":{"inner":123}} Y'
    assert extract_json_from_text(text) == {"outer": {"inner": 123}}

def test_extract_json_no_json():
    with pytest.raises(ValueError):
        extract_json_from_text("no json here")

def test_transform_query_to_json(monkeypatch):
    fake = {"location":"Test","date":"2025-01-01","latitude":None,"longitude":None}
    # mock LLM API
    monkeypatch.setattr("chatbot.requests.post",
        lambda *args, **kwargs: DummyResponse({"choices":[{"message":{"content": json.dumps(fake)}}]}))
    out = transform_query_to_json("What is weather?")
    assert out == fake

def test_build_openmeteo_json(monkeypatch):
    base = {"location":"Loc","date":"2025-02-02","latitude":None,"longitude":None}
    # mock interní funkce
    monkeypatch.setattr("chatbot.transform_query_to_json", lambda q: base.copy())
    monkeypatch.setattr("chatbot.get_coordinates", lambda loc: (12.34, 56.78))
    res = build_openmeteo_json("dummy")
    assert res["latitude"] == 12.34 and res["longitude"] == 56.78
