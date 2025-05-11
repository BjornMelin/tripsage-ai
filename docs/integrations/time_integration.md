# Time MCP Server Integration

This document outlines the implementation details for the Time MCP Server, which provides timezone conversion and time management capabilities for the TripSage travel planning system.

## Overview

The Time MCP Server provides essential time-related functionality for the TripSage application, including timezone conversion, date manipulation, and scheduling utilities. These capabilities are critical for a travel planning system that must coordinate activities across multiple timezones, manage flight arrival and departure times, and create accurate itineraries with proper local time information.

## Technology Selection

After evaluating multiple time management libraries and implementation approaches, we selected the following technology stack:

- **Official MCP Time Server**: Standardized server from the Model Context Protocol (MCP) ecosystem
- **Python**: Core language for the time server implementation
- **ZoneInfo**: Standard library for timezone management and calculations
- **DateTime**: Python's built-in datetime library for comprehensive time handling
- **OpenAI Agents SDK**: For integration with our agent-based architecture
- **Docker**: For containerized deployment

The official MCP time server was chosen over custom implementations for the following reasons:

- Standardized implementation following MCP best practices
- Well-maintained as part of the ModelContextProtocol ecosystem
- Proper handling of DST (Daylight Saving Time) transitions
- Support for timezone manipulation with IANA timezone names
- Robust error handling and validation
- Active maintenance and modern design

## MCP Tools

The Time MCP Server exposes the following key tools:

### get_current_time

Retrieves the current time in a specific timezone.

```python
@mcp.tool()
async def get_current_time(
    timezone: str
) -> dict:
    """Get current time in a specific timezone.

    Args:
        timezone: IANA timezone name (e.g., 'America/New_York', 'Europe/London').
                 Use 'UTC' as local timezone if no timezone provided by the user.

    Returns:
        A dictionary containing:
        - timezone: The specified timezone
        - datetime: Current datetime in ISO 8601 format
        - is_dst: Whether DST is active in the specified timezone
    """
    try:
        # Validate timezone
        tz = ZoneInfo(timezone)

        # Get current time in the specified timezone
        now = datetime.now(tz)

        return {
            "timezone": timezone,
            "datetime": now.isoformat(),
            "is_dst": now.dst() != timedelta(0)
        }
    except Exception as e:
        raise ValueError(f"Error getting current time: {str(e)}")
```

### convert_time

Converts a time from one timezone to another.

```python
@mcp.tool()
async def convert_time(
    source_timezone: str,
    time: str,
    target_timezone: str
) -> dict:
    """Convert time between timezones.

    Args:
        source_timezone: Source IANA timezone name (e.g., 'America/New_York', 'Europe/London').
                         Use 'UTC' as local timezone if no source timezone provided by the user.
        time: Time to convert in 24-hour format (HH:MM)
        target_timezone: Target IANA timezone name (e.g., 'Asia/Tokyo', 'America/San_Francisco').
                         Use 'UTC' as local timezone if no target timezone provided by the user.

    Returns:
        A dictionary containing:
        - source: Source timezone information (timezone, datetime, is_dst)
        - target: Target timezone information (timezone, datetime, is_dst)
        - time_difference: String representation of the time difference (e.g., '+9.0h')
    """
    try:
        # Validate timezones
        source_tz = ZoneInfo(source_timezone)
        target_tz = ZoneInfo(target_timezone)

        # Parse time (assuming current day)
        hour, minute = map(int, time.split(':'))
        now = datetime.now()
        source_dt = datetime(
            now.year, now.month, now.day,
            hour, minute, 0, 0,
            tzinfo=source_tz
        )

        # Convert to target timezone
        target_dt = source_dt.astimezone(target_tz)

        # Calculate time difference in hours
        time_diff_hours = (target_dt.utcoffset() - source_dt.utcoffset()).total_seconds() / 3600
        time_diff_str = f"{'+' if time_diff_hours >= 0 else ''}{time_diff_hours}h"

        return {
            "source": {
                "timezone": source_timezone,
                "datetime": source_dt.isoformat(),
                "is_dst": source_dt.dst() != timedelta(0)
            },
            "target": {
                "timezone": target_timezone,
                "datetime": target_dt.isoformat(),
                "is_dst": target_dt.dst() != timedelta(0)
            },
            "time_difference": time_diff_str
        }
    except Exception as e:
        raise ValueError(f"Error converting time: {str(e)}")
```

## Implementation Details

### Server Architecture

The Time MCP Server follows the standard MCP server architecture:

1. **Core**: MCP server definition and configuration
2. **Tools**: MCP tool implementations for time-related functions
3. **Utils**: Helper functions for timezone validation and management

### Client Integration

TripSage integrates with the Time MCP Server in two ways:

#### 1. Claude Desktop Configuration

For Claude desktop integration, the time server configuration is added to the client configuration:

```javascript
// claude-settings.json
{
  "mcpServers": {
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"]
    }
  }
}
```

The Claude desktop interface directly interacts with the time server following the MCP protocol.

#### 2. OpenAI Agents SDK Integration

For the OpenAI Agents SDK integration, we use the MCPServerManager class to interface with the time server:

```python
# src/mcp/time/client.py
import os
from datetime import datetime
from typing import Dict, Optional

from agents import Agent, function_tool
from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class TimeMCPClient(BaseMCPClient):
    """Client for the Time MCP Server."""

    def __init__(self):
        """Initialize the Time MCP client."""
        super().__init__(server_name="time")
        logger.info("Initialized Time MCP Client")

    @function_tool
    async def get_current_time(self, timezone: str) -> Dict:
        """Get current time in a specific timezone.

        Args:
            timezone: IANA timezone name (e.g., 'America/New_York', 'Europe/London').
                     Use 'UTC' as local timezone if no timezone provided by the user.

        Returns:
            Dict with timezone information including current time
        """
        try:
            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool("get_current_time", {"timezone": timezone})
            return result
        except Exception as e:
            logger.error(f"Error getting current time: {str(e)}")
            # Fallback implementation if server fails
            return {
                "timezone": timezone,
                "datetime": datetime.now().isoformat(),
                "error": f"Server error: {str(e)}"
            }

    @function_tool
    async def convert_time(
        self,
        source_timezone: str,
        time: str,
        target_timezone: str
    ) -> Dict:
        """Convert time between timezones.

        Args:
            source_timezone: Source IANA timezone name (e.g., 'America/New_York').
                             Use 'UTC' as local timezone if no source timezone provided.
            time: Time to convert in 24-hour format (HH:MM)
            target_timezone: Target IANA timezone name (e.g., 'Asia/Tokyo').
                             Use 'UTC' as local timezone if no target timezone provided.

        Returns:
            Dict with source and target timezone information and time difference
        """
        try:
            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool(
                "convert_time",
                {
                    "source_timezone": source_timezone,
                    "time": time,
                    "target_timezone": target_timezone
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error converting time: {str(e)}")
            return {
                "error": f"Failed to convert time: {str(e)}",
                "source_timezone": source_timezone,
                "target_timezone": target_timezone,
                "time": time
            }

# Usage example:
async def create_time_enabled_agent() -> Agent:
    """Create an agent with time management capabilities.

    Returns:
        Agent configured with time management tools
    """
    from src.mcp.openai_agents_integration import create_agent_with_mcp_servers

    # Create client instance for function tools
    time_client = TimeMCPClient()

    # Create agent with MCP server
    agent = await create_agent_with_mcp_servers(
        name="Travel Agent",
        instructions="You are a travel planning assistant that helps plan itineraries across time zones.",
        server_names=["time"],
        tools=[
            time_client.get_current_time,
            time_client.convert_time
        ]
    )

    return agent
```

The server configuration is defined in the OpenAI Agents SDK configuration file:

```javascript
// mcp_servers/openai_agents_config.js
module.exports = {
  mcpServers: {
    time: {
      command: "uvx",
      args: ["mcp-server-time"],
      env: {
        PYTHONPATH: "${PYTHONPATH}",
      },
    },
    // Other MCP servers...
  },
};
```

## Integration with TripSage

The Time MCP Server integrates with TripSage in the following ways:

### Agent Integration

The Travel Agent uses the Time MCP Server for several key functions in the travel planning process:

1. **Flight Time Calculations**: Convert flight departure and arrival times between timezones
2. **Itinerary Planning**: Display activities in the correct local time for each destination
3. **Booking Optimization**: Determine optimal booking times across different timezones
4. **Timezone Awareness**: Provide contextual timezone information to travelers
5. **Travel Duration Management**: Calculate total travel time including timezone changes

### Data Flow

1. **Input**: Travel agent receives time information such as departure times and flight durations
2. **Processing**: The agent uses the Time MCP Server to calculate local times and make conversions
3. **Integration**: Timezone-adjusted times are incorporated into the travel plan
4. **Storage**: Time information is stored with proper timezone context in Supabase
5. **Presentation**: Times are formatted consistently across the itinerary

### Example Use Cases

- **International Flight Planning**: Converting departure and arrival times between origin and destination timezones
- **Multi-City Itinerary**: Ensuring activities in different cities use the correct local time
- **Jet Lag Management**: Calculating optimal sleep and wake times based on timezone changes
- **Booking Windows**: Determining the best time to book activities based on local business hours
- **Conference Call Scheduling**: Coordinating virtual meetings across multiple timezones

## Deployment and Configuration

### Environment Variables

| Variable       | Description                                   | Default |
| -------------- | --------------------------------------------- | ------- |
| LOCAL_TIMEZONE | Override system timezone for local operations | System  |

### Deployment Options

1. **With uvx (recommended)**:

   ```bash
   # Install if needed
   pip install uvx

   # Run directly
   uvx mcp-server-time
   ```

2. **With pip**:

   ```bash
   # Install the package
   pip install mcp-server-time

   # Run the server
   python -m mcp_server_time
   ```

3. **Docker Container**:

   ```bash
   # Build container with official MCP time server
   docker build -t time-mcp-server -f docker/timemcp/Dockerfile .

   # Run container
   docker run -p 3000:3000 time-mcp-server
   ```

4. **Local Development**:

   ```bash
   # Clone the repository
   git clone https://github.com/modelcontextprotocol/servers.git

   # Navigate to the time server directory
   cd servers/src/time

   # Run with MCP inspector for debugging
   npx @modelcontextprotocol/inspector uv run mcp-server-time
   ```

## Best Practices

1. **Timezone Names**: Always use IANA timezone names (e.g., "America/New_York") rather than abbreviations (e.g., "EST")
2. **Date Format**: Use ISO 8601 format (YYYY-MM-DD) for date interchange
3. **Time Zones vs. Offsets**: Store timezone names rather than offsets to handle DST changes
4. **Validation**: Validate timezone inputs to prevent errors
5. **Formatting**: Use locale-aware formatting for user-facing displays
6. **Error Handling**: Provide clear error messages for invalid inputs
7. **Caching**: Cache timezone data to improve performance

## Testing

For testing the time server integration, we utilize pytest and the MCP inspector:

```python
# src/mcp/time/tests/test_client.py
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.mcp.time.client import TimeMCPClient

@pytest.fixture
async def time_client():
    """Create a time client for testing."""
    client = TimeMCPClient()
    return client

@pytest.mark.asyncio
async def test_get_current_time(time_client):
    """Test getting current time."""
    # Test with valid timezone
    result = await time_client.get_current_time("America/New_York")
    assert "timezone" in result
    assert "datetime" in result
    assert result["timezone"] == "America/New_York"

    # Verify datetime is in the correct format
    datetime.fromisoformat(result["datetime"])  # Should not raise an exception

@pytest.mark.asyncio
async def test_convert_time(time_client):
    """Test converting time between timezones."""
    # Test with valid timezones
    result = await time_client.convert_time(
        "America/New_York",
        "14:30",
        "Asia/Tokyo"
    )

    assert "source" in result
    assert "target" in result
    assert "time_difference" in result

    assert result["source"]["timezone"] == "America/New_York"
    assert result["target"]["timezone"] == "Asia/Tokyo"

    # Verify expected time difference
    tokyo = ZoneInfo("Asia/Tokyo")
    ny = ZoneInfo("America/New_York")
    now = datetime.now()
    expected_diff_hours = (
        datetime(now.year, now.month, now.day, tzinfo=tokyo).utcoffset() -
        datetime(now.year, now.month, now.day, tzinfo=ny).utcoffset()
    ).total_seconds() / 3600

    diff_str = result["time_difference"].replace("h", "")
    actual_diff = float(diff_str)
    assert abs(actual_diff - expected_diff_hours) < 0.01  # Allow small precision differences
```

## Limitations and Future Enhancements

### Current Limitations

- Limited to basic timezone conversion and current time retrieval
- No support for astronomical time calculations (sunrise/sunset)
- Limited calendar functionality
- No built-in travel time calculation (we must implement this ourselves)

### Planned Enhancements

1. **Calendar Integration**: Add tools for creating and managing calendar events
2. **Working Hours**: Support for calculating business hours across timezones
3. **Sunrise/Sunset Calculations**: Add support for calculating dawn/dusk times for locations
4. **Historical Time Data**: Extend support for historical timezone changes
5. **Natural Language Processing**: Parse relative time expressions (e.g., "next Monday")
6. **Flight Schedule Integration**: Direct integration with flight APIs for accurate timezone handling

## Conclusion

The Time MCP Server provides essential timezone and time management capabilities for the TripSage travel planning system using the official MCP implementation. By offering tools for timezone conversion and current time retrieval, it enables TripSage to provide accurate, timezone-aware travel plans. The implementation leverages the standardized Model Context Protocol, ensuring compatibility with modern AI agent frameworks including both Claude Desktop and OpenAI Agents SDK.

This integration is particularly critical for international travel planning, where accurate timezone information can significantly impact the travel experience. Our implementation provides a flexible approach that works with different agent frameworks while maintaining consistent functionality.
