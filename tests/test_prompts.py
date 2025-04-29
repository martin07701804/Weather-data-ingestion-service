import pytest
from prompts import ROLE_SYSTEM, ROLE_USER, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, weather_user_prompt
from langchain.prompts import PromptTemplate


def test_role_constants():
    assert ROLE_SYSTEM == "system"
    assert ROLE_USER == "user"


def test_system_prompt_format_and_content():
    # Format the SYSTEM_PROMPT with a sample date
    sample_date = "2025-04-29"
    formatted = SYSTEM_PROMPT.format(current_date=sample_date)
    # The placeholder should be replaced
    assert "{current_date}" not in formatted
    assert sample_date in formatted
    # Check key sections exist
    assert formatted.startswith("Directly convert")
    assert "**Instructions:**" in formatted
    assert "Respond with ONLY the JSON object" in formatted


def test_user_prompt_template_structure():
    # weather_user_prompt should be a PromptTemplate
    assert isinstance(weather_user_prompt, PromptTemplate)
    # It should use the USER_PROMPT_TEMPLATE and expect 'query'
    assert weather_user_prompt.template == USER_PROMPT_TEMPLATE
    assert weather_user_prompt.input_variables == ["query"]


def test_weather_user_prompt_formatting():
    query = "What is the UV index in Brno tomorrow?"
    rendered = weather_user_prompt.format(query=query)
    # It should embed the query in the template
    assert f"User Query: {query}" in rendered
    # Leading/trailing whitespace handling
    assert rendered.strip() == f"User Query: {query}"
