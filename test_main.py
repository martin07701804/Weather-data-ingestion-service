import pytest
import main
import chatbot


def test_constants_api_costs_structure():
    # Check API_COSTS dict exists and has expected keys and numeric values
    assert isinstance(main.API_COSTS, dict)
    expected_keys = {"llm", "geocoding", "meteo_archive", "meteo_forecast"}
    assert set(main.API_COSTS.keys()) == expected_keys
    for key, value in main.API_COSTS.items():
        assert isinstance(value, (int, float)), f"API_COSTS[{key}] should be numeric"


def test_cost_currency_type():
    # Check COST_CURRENCY is a non-empty string
    assert hasattr(main, "COST_CURRENCY"), "COST_CURRENCY is not defined"
    assert isinstance(main.COST_CURRENCY, str)
    assert main.COST_CURRENCY.strip() != ""


def test_imported_chatbot_functions_exist():
    # Ensure main imports necessary functions from chatbot module
    for func_name in ["build_openmeteo_json", "fetch_weather_data", "filter_data_by_granularity"]:
        assert hasattr(chatbot, func_name), f"chatbot.{func_name} should exist"
        assert callable(getattr(chatbot, func_name)), f"chatbot.{func_name} should be callable"


def test_main_module_syntax():
    # Importing main should not produce errors
    # This test simply verifies that the module loads
    assert main is not None
