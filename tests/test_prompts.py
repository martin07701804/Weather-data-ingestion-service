import os
import sys
import pytest
from langchain.prompts import PromptTemplate

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from prompts import weather_prompt, prompt_template

def test_weather_prompt_is_instance_and_input_variables():
    """weather_prompt should be a PromptTemplate with input_variables ['query'].""" 
    assert isinstance(weather_prompt, PromptTemplate)
    assert weather_prompt.input_variables == ["query"]

def test_prompt_template_contains_required_keys():
    """The template string must include all required JSON fields."""
    tpl = prompt_template
    assert '"location": "<location>"' in tpl
    assert '"date_from": "<date in YYYY-MM-DD>"' in tpl
    assert '"date_to": "<date in YYYY-MM-DD>"' in tpl
    assert '"granularity": "<In minutes>"' in tpl
    assert '"latitude": null' in tpl
    assert '"longitude": null' in tpl

def test_prompt_template_has_granularity_default_instruction():
    """Ensure the instructions mention the default granularity of 60."""
    assert "leave the field as 60" in prompt_template

def test_format_injects_query_and_preserves_structure():
    """
    Calling weather_prompt.format(query=...)
    should insert the query line and keep the overall structure.
    """
    sample_query = "What is the UV index in Prague tomorrow?"
    formatted = weather_prompt.format(query=sample_query)

    # It should begin with the defined prompt intro
    assert formatted.strip().startswith("You are an assistant that converts natural language weather queries into JSON.")
    # It should include the Query line with our sample
    assert f"Query: {sample_query}" in formatted
    # It should still contain the JSON placeholders
    assert '"location": "<location>"' in formatted
    assert '"granularity": "<In minutes>"' in formatted
