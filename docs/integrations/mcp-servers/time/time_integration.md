# Time MCP Server Integration

This document outlines the implementation of the Time MCP Server integration for the TripSage travel planning system.

## Overview

The Time MCP Server provides essential time-related functionality for the TripSage application, including:

- Current time retrieval in different timezones
- Timezone conversion
- Travel time calculation considering timezone differences
- Meeting time scheduling across multiple timezones
- Creation of timezone-aware travel itineraries

These capabilities are critical for a travel planning system that must coordinate activities across multiple timezones, manage flight arrival and departure times, and create accurate itineraries with proper local time information.

## Integration with Official MCP Time Server

TripSage integrates with the official Model Context Protocol Time Server to handle all time-related operations. This server is maintained by the Model Context Protocol team and provides standardized time and timezone capabilities.

### Official Time MCP Server Features

- Current time retrieval with IANA timezone support
- Timezone conversion with proper DST handling
- System timezone auto-detection
- High-quality timezone database with worldwide coverage

## Implementation Details

The integration consists of several components:

1. **Time MCP Client**: A wrapper for the official Time MCP server
2. **Time Service**: High-level service with travel-specific time features
3. **Agent Function Tools**: OpenAI Agents SDK tools for time operations
4. **Deployment Scripts**: For easily running the Time MCP server

### Client Implementation

The `TimeMCPClient` class in `src/mcp/time/client.py` provides a clean interface to the Time MCP server with the following key methods:

- `get_current_time(timezone)`: Get current time in a specific timezone
- `convert_time(time, source_timezone, target_timezone)`: Convert time between timezones

The client handles error handling, response parsing, and request caching for optimal performance.

### Time Service Implementation

The `TimeService` class in `src/mcp/time/client.py` builds upon the basic Time MCP client to provide travel-specific functionality:

- `get_local_time(location)`: Maps location names to timezones and gets local time
- `calculate_flight_arrival(departure_time, departure_timezone, flight_duration_hours, arrival_timezone)`: Calculates arrival time considering timezone differences
- `create_timezone_aware_itinerary(itinerary_items)`: Adds timezone information to travel itineraries
- `find_meeting_times(first_timezone, second_timezone, ...)`: Finds suitable meeting times across timezones

### Agent Function Tools

TripSage provides a set of function tools in `src/agents/time_tools.py` that can be used by both Claude Code and OpenAI Agents:

- `get_current_time_tool`: Get current time in a specific timezone
- `convert_timezone_tool`: Convert time between timezones
- `get_local_time_tool`: Get local time for a travel destination
- `calculate_flight_arrival_tool`: Calculate flight arrival time considering timezones
- `find_meeting_times_tool`: Find suitable meeting times across different timezones
- `create_timezone_aware_itinerary_tool`: Create timezone-aware travel itineraries

These tools enable agents to handle complex time-related questions for travel planning.

## Deployment

TripSage provides deployment scripts for the Time MCP server in the `scripts` directory:

- `start_time_mcp.sh`: Install and start the Time MCP server
- `stop_time_mcp.sh`: Stop the running Time MCP server

The server is automatically configured to use local system timezone and runs on port 8004 by default.

### Configuration

To configure the Time MCP client, set the following environment variables:

```
TIME_MCP_SERVER_URL=http://localhost:8004
TIME_MCP_PORT=8004 # Optional, defaults to 8004
```

## Example Usage

### Getting Current Time

```python
from src.mcp.time.client import get_client

time_client = get_client()
tokyo_time = await time_client.get_current_time("Asia/Tokyo")
print(f"Current time in Tokyo: {tokyo_time['current_time']}")
```

### Converting Between Timezones

```python
from src.mcp.time.client import get_client

time_client = get_client()
conversion = await time_client.convert_time(
    time="14:30",
    source_timezone="America/New_York",
    target_timezone="Europe/London"
)
print(f"14:30 in New York is {conversion['target_time']} in London")
```

### Calculating Flight Arrival Time

```python
from src.mcp.time.client import get_service

time_service = get_service()
arrival_info = await time_service.calculate_flight_arrival(
    departure_time="14:30",
    departure_timezone="America/New_York",
    flight_duration_hours=7.5,
    arrival_timezone="Europe/London"
)
print(f"Flight arrives at {arrival_info['arrival_time_local']} local time")
```

### Using Agent Function Tools

```python
from src.agents import Agent
from src.agents.time_tools import (
    get_current_time_tool,
    convert_timezone_tool,
    calculate_flight_arrival_tool
)

# Create a time-aware travel agent
time_agent = Agent(
    name="Time-Aware Travel Agent",
    instructions="You help travelers with time-related travel questions",
    tools=[
        get_current_time_tool,
        convert_timezone_tool,
        calculate_flight_arrival_tool
    ]
)
```

## Testing

The Time MCP integration includes comprehensive tests:

- `tests/mcp/time/test_time_client.py`: Tests for the Time MCP client and service
- `tests/agents/test_time_tools.py`: Tests for the agent function tools

Run the tests with:

```bash
python -m pytest tests/mcp/time tests/agents/test_time_tools.py -v
```

## Conclusion

The Time MCP Server integration provides TripSage with robust time and timezone capabilities, ensuring accurate travel time calculations and timezone-aware itineraries. By leveraging the official Model Context Protocol Time Server, TripSage benefits from standardized, well-maintained time functionality that enhances the accuracy of travel planning.