
import json
import pytest

import chatbot

# --- Helpers --------------------------------------------------------------

class DummyResponse:
    """Simulates requests.Response with a json() method."""
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

# --- Tests for extract_json_from_text ------------------------------------

def test_extract_json_simple():
    """Should extract a simple flat JSON object from text."""
    text = 'prefix {"key":"value"} suffix'
    result = chatbot.extract_json_from_text(text)
    assert result == {"key": "value"}

def test_extract_json_nested():
    """Should extract a nested JSON object from text."""
    text = 'X {"outer":{"inner":123}} Y'
    result = chatbot.extract_json_from_text(text)
    assert result == {"outer": {"inner": 123}}

def test_extract_json_no_json():
    """Should raise ValueError if no JSON is present."""
    with pytest.raises(ValueError):
        chatbot.extract_json_from_text("no json here")

# --- Tests for transform_query_to_json -----------------------------------

def test_transform_query_to_json_success(monkeypatch):
    """
    Should call the LLM API and return parsed JSON.
    We mock weather_prompt.format and requests.post.
    """
    # 1) stub out prompt formatting
    class FakePrompt:
        def format(self, query):
            return f"PROMPT: {query}"
    monkeypatch.setattr(chatbot, "weather_prompt", FakePrompt())

    # 2) stub out requests.post to return our fake JSON
    fake_payload = {
        "choices": [
            {"message": {"content": json.dumps({
                "location": "TestCity",
                "date": "2025-05-01",
                "latitude": None,
                "longitude": None
            })}}
        ]
    }
    monkeypatch.setattr(chatbot.requests, "post", lambda *args, **kwargs: DummyResponse(fake_payload))

    # 3) call and assert
    out = chatbot.transform_query_to_json("How's the weather?")
    assert out == {
        "location": "TestCity",
        "date": "2025-05-01",
        "latitude": None,
        "longitude": None
    }

# --- Tests for build_openmeteo_json ---------------------------------------

def test_build_openmeteo_json(monkeypatch):
    """
    Should enrich JSON from transform_query_to_json with coordinates
    using get_coordinates.
    """
    # 1) stub transform_query_to_json
    monkeypatch.setattr(chatbot, "transform_query_to_json",
                        lambda q: {"location": "Praha", "date": "2025-05-02", "latitude": None, "longitude": None})
    # 2) stub get_coordinates
    monkeypatch.setattr(chatbot, "get_coordinates", lambda loc: (50.0755, 14.4378))

    # 3) call and verify
    result = chatbot.build_openmeteo_json("dummy query")
    assert result["location"] == "Praha"
    assert result["date"] == "2025-05-02"
    assert result["latitude"] == 50.0755
    assert result["longitude"] == 14.4378
