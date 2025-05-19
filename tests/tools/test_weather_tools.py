"""
Tests for weather tools.

This module tests the weather function tools to ensure they correctly interact with
the Weather MCP server and properly handle responses and errors.
"""

from unittest.mock import patch

import pytest

from tripsage.tools.weather_tools import (
    compare_destinations_weather_tool,
    get_destination_weather_tool,
    get_optimal_travel_time_tool,
    get_trip_weather_summary_tool,
)


@pytest.mark.asyncio
@patch("tripsage.tools.weather_tools.get_current_weather_tool")
async def test_get_destination_weather(mock_get_current_weather):
    # Arrange
    mock_get_current_weather.return_value = {
        "temperature": 22.5,
        "feels_like": 24.0,
        "weather": {"main": "Clear", "description": "clear sky"},
        "location": {"name": "Paris", "country": "FR"},
    }

    # Act
    result = await get_destination_weather_tool("Paris, FR")

    # Assert
    assert mock_get_current_weather.called
    assert mock_get_current_weather.call_args[1] == {"city": "Paris", "country": "FR"}
    assert "destination" in result
    assert result["destination"] == "Paris, FR"
    assert result["temperature"] == 22.5


@pytest.mark.asyncio
@patch("tripsage.tools.weather_tools.get_weather_forecast_tool")
async def test_get_trip_weather_summary(mock_get_forecast):
    # Arrange
    mock_get_forecast.return_value = {
        "daily": [
            {
                "date": "2025-05-20",
                "temp_min": 18.0,
                "temp_max": 25.0,
                "temp_avg": 21.5,
                "weather": {"main": "Clear", "description": "clear sky"},
            },
            {
                "date": "2025-05-21",
                "temp_min": 17.0,
                "temp_max": 24.0,
                "temp_avg": 20.5,
                "weather": {"main": "Clear", "description": "clear sky"},
            },
            {
                "date": "2025-05-22",
                "temp_min": 16.0,
                "temp_max": 23.0,
                "temp_avg": 19.5,
                "weather": {"main": "Rain", "description": "light rain"},
            },
        ],
        "location": {"name": "Paris", "country": "FR"},
    }

    # Act
    result = await get_trip_weather_summary_tool(
        "Paris, FR", "2025-05-20", "2025-05-22"
    )

    # Assert
    assert mock_get_forecast.called
    assert mock_get_forecast.call_args[1] == {
        "city": "Paris",
        "country": "FR",
        "days": 16,
    }
    assert result["destination"] == "Paris, FR"
    assert result["start_date"] == "2025-05-20"
    assert result["end_date"] == "2025-05-22"
    assert result["temperature"]["average"] == 20.5  # (21.5 + 20.5 + 19.5) / 3
    assert result["temperature"]["min"] == 16.0
    assert result["temperature"]["max"] == 25.0
    assert result["conditions"]["most_common"] == "Clear"
    assert result["conditions"]["frequency"] == 2 / 3
    assert len(result["days"]) == 3


@pytest.mark.asyncio
@patch("tripsage.tools.weather_tools.get_current_weather_tool")
@patch("tripsage.tools.weather_tools.get_weather_forecast_tool")
async def test_compare_destinations_weather(
    mock_get_forecast, mock_get_current_weather
):
    # Arrange
    mock_get_current_weather.side_effect = [
        {
            "temperature": 22.5,
            "feels_like": 24.0,
            "weather": {"main": "Clear", "description": "clear sky"},
        },
        {
            "temperature": 18.0,
            "feels_like": 17.0,
            "weather": {"main": "Rain", "description": "light rain"},
        },
    ]

    # Act
    result = await compare_destinations_weather_tool(["Paris, FR", "London, UK"])

    # Assert
    assert mock_get_current_weather.call_count == 2
    assert len(result["results"]) == 2
    assert result["ranking"] == ["Paris, FR", "London, UK"]  # Ranked by temperature


@pytest.mark.asyncio
@patch("tripsage.tools.weather_tools.get_travel_recommendation_tool")
async def test_get_optimal_travel_time(mock_get_recommendation):
    # Arrange
    mock_get_recommendation.return_value = {
        "current_weather": {
            "temperature": 22.5,
            "weather": {"main": "Clear"},
        },
        "recommendations": {
            "activities": ["For beach activities, the weather is perfect now"],
            "forecast_based": ["Good weather expected for the next 5 days"],
            "clothing": ["Light summer clothes", "Sunscreen"],
        },
    }

    # Act
    result = await get_optimal_travel_time_tool("Miami, US", "beach")

    # Assert
    assert mock_get_recommendation.called
    assert mock_get_recommendation.call_args[1] == {
        "city": "Miami",
        "country": "US",
        "activities": ["beach"],
    }
    assert result["destination"] == "Miami, US"
    assert result["activity_type"] == "beach"
    assert result["current_weather"] == "Clear"
    assert result["current_temp"] == 22.5
    assert (
        result["activity_recommendation"]
        == "For beach activities, the weather is perfect now"
    )
    assert "formatted" in result
