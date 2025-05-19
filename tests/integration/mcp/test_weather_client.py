#!/usr/bin/env python3
"""
Test script for the Weather MCP Client.

This script tests basic functionality of the Weather MCP Client implementation.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

from src.mcp.weather import get_client, get_service


async def test_get_current_weather():
    """Test the get_current_weather method."""
    client = get_client()
    result = await client.get_current_weather(city="Paris", country="FR")
    print("Current Weather in Paris:")
    print(json.dumps(result, indent=2))
    return result


async def test_get_forecast():
    """Test the get_forecast method."""
    client = get_client()
    result = await client.get_forecast(city="London", country="GB", days=3)
    print("\nWeather Forecast for London (3 days):")
    print(json.dumps(result, indent=2))
    return result


async def test_get_travel_recommendation():
    """Test the get_travel_recommendation method."""
    client = get_client()
    result = await client.get_travel_recommendation(
        city="Barcelona", country="ES", activities=["beach", "sightseeing"]
    )
    print("\nTravel Recommendations for Barcelona:")
    print(json.dumps(result, indent=2))
    return result


async def test_weather_service():
    """Test the WeatherService methods."""
    service = get_service()

    # Test destination weather
    dest_weather = await service.get_destination_weather("Tokyo, JP")
    print("\nDestination Weather for Tokyo:")
    print(json.dumps(dest_weather, indent=2))

    # Test trip weather summary
    trip_summary = await service.get_trip_weather_summary(
        destination="New York, US", start_date="2023-07-01", end_date="2023-07-07"
    )
    print("\nTrip Weather Summary for New York:")
    print(trip_summary.model_dump_json(indent=2))

    # Test destination comparison
    comparison = await service.compare_destinations_weather(
        destinations=["Miami, US", "Cancun, MX", "Phuket, TH"], date="2023-08-15"
    )
    print("\nDestination Weather Comparison:")
    print(comparison.model_dump_json(indent=2))

    # Test optimal travel time
    optimal_time = await service.get_optimal_travel_time(
        destination="Aspen, US", activity_type="skiing"
    )
    print("\nOptimal Travel Time for Skiing in Aspen:")
    print(optimal_time.model_dump_json(indent=2))


async def main():
    """Run all tests."""
    try:
        await test_get_current_weather()
        await test_get_forecast()
        await test_get_travel_recommendation()
        await test_weather_service()
        print("\nAll tests completed successfully!")
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
