import pytest
from langchain.prompts import PromptTemplate

from prompts import weather_prompt, prompt_template

def test_weather_prompt_is_prompttemplate():
    # Instance a vstupní proměnné
    assert isinstance(weather_prompt, PromptTemplate)
    assert weather_prompt.input_variables == ["query"]

def test_prompt_template_equals_definition():
    # Ověříme, že template v objektu odpovídá definici
    assert weather_prompt.template == prompt_template

def test_format_inserts_query_and_keeps_structure():
    sample_query = "What's the UV index in Prague tomorrow?"
    formatted = weather_prompt.format(query=sample_query)


    assert f"Query: {sample_query}" in formatted


    assert '"location": "<location>"' in formatted
    assert '"date": "<date>"' in formatted
    assert '"latitude": null' in formatted
    assert '"longitude": null' in formatted

    # Základní úvodní text
    assert formatted.strip().startswith("You are an assistant that converts natural language weather queries into JSON.")
