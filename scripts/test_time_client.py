#!/usr/bin/env python3
"""
Test script for the Time MCP Client.

This script tests basic functionality of the Time MCP Client implementation.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

from src.mcp.time import get_client, get_service


async def test_get_current_time():
    """Test the get_current_time method."""
    client = get_client()
    result = await client.get_current_time(timezone="America/New_York")
    print("Current Time in New York:")
    print(json.dumps(result, indent=2))
    return result


async def test_convert_time():
    """Test the convert_time method."""
    client = get_client()
    result = await client.convert_time(
        time="14:30",
        source_timezone="America/New_York",
        target_timezone="Europe/London",
    )
    print("\nTime Conversion from New York to London (14:30):")
    print(json.dumps(result, indent=2))
    return result


async def test_calculate_travel_time():
    """Test the calculate_travel_time method."""
    client = get_client()
    result = await client.calculate_travel_time(
        departure_timezone="America/New_York",
        departure_time="14:30",
        arrival_timezone="Europe/London",
        arrival_time="02:30",
    )
    print("\nTravel Time Calculation:")
    print(json.dumps(result, indent=2))
    return result


async def test_list_timezones():
    """Test the list_timezones method."""
    client = get_client()
    result = await client.list_timezones()
    print("\nTimezones List (showing first 5):")
    print(
        json.dumps(
            {"timezones": result["timezones"][:5], "count": result["count"]}, indent=2
        )
    )

    print("\nTimezones Grouped by Region (showing first region):")
    first_region = next(iter(result["grouped_timezones"]))
    print(
        json.dumps({first_region: result["grouped_timezones"][first_region]}, indent=2)
    )

    return result


async def test_format_date():
    """Test the format_date method."""
    client = get_client()
    formats = ["full", "short", "date_only", "time_only", "iso"]

    print("\nDate Formatting Examples:")
    for format_type in formats:
        result = await client.format_date(
            date="2025-07-04T10:30:00",
            timezone="America/Los_Angeles",
            format=format_type,
        )
        print(f"{format_type.upper()}: {result['formatted_date']}")

    return result


async def test_time_service():
    """Test the high-level time service methods."""
    service = get_service()

    # Test local time lookup
    local_time = await service.get_local_time("Tokyo")
    print("\nLocal Time in Tokyo:")
    print(json.dumps(local_time, indent=2))

    # Test flight arrival calculation
    flight_arrival = await service.calculate_flight_arrival(
        departure_time="08:00",
        departure_timezone="America/New_York",
        flight_duration_hours=7.5,
        arrival_timezone="Europe/Paris",
    )
    print("\nFlight Arrival Calculation (NY to Paris, 7.5 hours):")
    print(json.dumps(flight_arrival, indent=2))

    # Test timezone-aware itinerary
    itinerary_items = [
        {"location": "New York", "activity": "Depart JFK", "time": "08:00"},
        {"location": "Paris", "activity": "Arrive CDG", "time": "19:30"},
        {"location": "Paris", "activity": "Check-in Hotel", "time": "21:00"},
    ]

    timezone_itinerary = await service.create_timezone_aware_itinerary(itinerary_items)
    print("\nTimezone-aware Itinerary:")
    print(json.dumps(timezone_itinerary, indent=2))

    # Test meeting time finder
    meeting_times = await service.find_meeting_times(
        first_timezone="America/Los_Angeles",
        second_timezone="Asia/Tokyo",
        first_available_hours=(9, 17),
        second_available_hours=(9, 17),
    )
    print("\nSuitable Meeting Times (LA and Tokyo, showing first 2):")
    print(json.dumps(meeting_times[:2], indent=2))


async def main():
    """Run all tests."""
    try:
        await test_get_current_time()
        await test_convert_time()
        await test_calculate_travel_time()
        await test_list_timezones()
        await test_format_date()
        await test_time_service()
        print("\nAll tests completed successfully!")
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
