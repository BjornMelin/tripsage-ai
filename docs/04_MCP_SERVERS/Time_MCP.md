# Time MCP Server Integration Guide

This document outlines the integration and usage of the Time MCP Server within the TripSage AI Travel Planning System.

## 1. Overview

Accurate time and timezone management are critical for a travel planning application like TripSage. The Time MCP Server provides essential time-related functionalities, including:

- Retrieving the current time in various IANA timezones.
- Converting times between different timezones, correctly handling Daylight Saving Time (DST).
- Calculating travel durations considering timezone differences.
- Assisting in scheduling meetings or activities across multiple timezones.
- Ensuring all itinerary items are displayed with correct local times.

## 2. Integration with the Official Time MCP Server

TripSage integrates with the **official Model Context Protocol Time Server** (`@uvx/mcp-server-time` or its Python equivalent if one becomes official and preferred). This server is maintained by the MCP community or a dedicated team and provides standardized, reliable time and timezone capabilities.

### 2.1. Rationale for Using the Official Server

- **Standardization**: Adheres to MCP specifications and uses a comprehensive, up-to-date timezone database (typically IANA).
- **Reliability & Maintenance**: Leverages a community-maintained or officially supported package, reducing TripSage's internal maintenance burden for this common utility.
- **Accuracy**: Provides accurate DST handling and timezone conversions.
- **Simplicity**: Offers a straightforward set of tools for common time operations.

### 2.2. Key Features of the Official Time MCP Server

- Current time retrieval with IANA timezone support.
- Timezone conversion.
- System timezone auto-detection (for the server itself).
- Access to a high-quality timezone database.

### 2.3. Running the Official Time MCP Server

The official Time MCP server can be run using various methods. TripSage includes scripts to simplify this process for development:

- **`scripts/start_official_time_mcp.sh`**: This script typically handles:
  - Checking if the MCP server package (e.g., `@uvx/mcp-server-time` for Node.js, or a Python equivalent) is installed.
  - Installing it globally or locally if missing (e.g., via `npx uvx mcp-server-time` or `uv pip install mcp-time-server`).
  - Starting the server, usually on a default port (e.g., 3000 or as configured).

**Example `start_official_time_mcp.sh` content (conceptual for a Node.js based server):**

```bash
#!/bin/bash
# scripts/start_official_time_mcp.sh

MCP_TIME_SERVER_PACKAGE="@uvx/mcp-server-time" # Example package name
MCP_PORT="${TIME_MCP_PORT:-3000}" # Use environment variable or default

# Check if npx is available (common for Node.js based MCPs)
if ! command -v npx &> /dev/null
then
    echo "npx could not be found. Please install Node.js and npm."
    exit 1
fi

echo "Starting Official Time MCP Server on port ${MCP_PORT}..."
# The command might vary based on the actual package
# This example assumes a Node.js package executable via npx
npx "${MCP_TIME_SERVER_PACKAGE}" --port "${MCP_PORT}"
```

## 3. TripSage Time MCP Client (TimeMCPClient)

TripSage interacts with the Time MCP server via a dedicated Python client, TimeMCPClient, located in src/mcp/time/client.py. This client acts as a wrapper, providing type-safe methods and integrating with TripSage's MCP Abstraction Layer.

### 3.1. Client Implementation Highlights

Inherits from BaseMCPClient.
Configured via centralized settings (endpoint URL for the Time MCP server).
Provides methods mapping to the Time MCP server's tools.

```python
# src/mcp/time/client.py (Simplified Snippet)
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from ..base_mcp_client import BaseMCPClient
from ...utils.config import settings
from ...utils.logging import get_module_logger
from agents import function_tool # For OpenAI Agent SDK integration

logger = get_module_logger(__name__)

class TimeZoneParams(BaseModel):
    timezone: str = Field(..., description="IANA timezone string (e.g., 'America/New_York', 'Europe/London').")

class ConvertTimeParams(BaseModel):
    time_string: str = Field(..., description="Time to convert (e.g., '14:30:00' or '2024-07-15T14:30:00').")
    source_timezone: str = Field(..., description="IANA timezone of the source time.")
    target_timezone: str = Field(..., description="IANA timezone for the target conversion.")
    date_string: Optional[str] = Field(None, description="Optional date (YYYY-MM-DD) if time_string is only time.")

class TimeMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="time", # Matches key in settings.mcp_servers
            endpoint=settings.mcp_servers.time.endpoint,
            # API key usually not needed for standard Time MCP
        )
        logger.info("Initialized Time MCP Client.")

    @function_tool
    async def get_current_time(self, timezone: str) -> Dict[str, Any]:
        """Gets the current time in the specified IANA timezone."""
        validated_params = TimeZoneParams(timezone=timezone)
        return await self.invoke_tool("get_current_time", validated_params.model_dump())

    @function_tool
    async def convert_time(self, time_string: str, source_timezone: str, target_timezone: str, date_string: Optional[str] = None) -> Dict[str, Any]:
        """Converts a time from a source timezone to a target timezone."""
        validated_params = ConvertTimeParams(
            time_string=time_string,
            source_timezone=source_timezone,
            target_timezone=target_timezone,
            date_string=date_string
        )
        return await self.invoke_tool("convert_time", validated_params.model_dump(exclude_none=True))

# Global client instance or factory function
# time_mcp_client = TimeMCPClient()
def get_time_mcp_client() -> TimeMCPClient:
    # Add logic for singleton if needed
    return TimeMCPClient()
```

### 3.2. Expected Response Format from Official Time MCP

The TimeMCPClient is designed to parse responses from the official Time MCP server, which typically follow a standard format.

For `get_current_time`:

```json
{
  "timezone": "America/New_York",
  "datetime": "2025-05-16T10:30:45-04:00", // ISO 8601 format
  "is_dst": true,
  "utc_offset": "-04:00"
}
```

For `convert_time`:

```json
{
  "source": {
    "timezone": "America/New_York",
    "datetime": "2025-05-16T14:30:00-04:00"
  },
  "target": {
    "timezone": "Europe/London",
    "datetime": "2025-05-16T19:30:00+01:00"
  },
  "time_difference_hours": 5.0 // Example
}
```

The client methods transform these responses into Python-friendly objects or dictionaries.

## 4. TripSage Time Service (TimeService)

Building on the TimeMCPClient, a higher-level TimeService (e.g., in src/services/time_service.py or as part of the client file) provides travel-specific time functionalities:

```python
# Part of src/mcp/time/client.py or a separate src/services/time_service.py
from datetime import datetime, timedelta, time

class TripSageTimeService:
    def __init__(self, client: TimeMCPClient):
        self.time_mcp_client = client

    async def get_local_time_for_destination(self, destination_name: str, destination_timezone: str) -> Optional[str]:
        """Gets the current local time for a given travel destination."""
        try:
            current_time_data = await self.time_mcp_client.get_current_time(timezone=destination_timezone)
            # Assuming datetime is in ISO format "YYYY-MM-DDTHH:MM:SSZ" or "YYYY-MM-DDTHH:MM:SS+/-HH:MM"
            dt_obj = datetime.fromisoformat(current_time_data['datetime'])
            return dt_obj.strftime('%Y-%m-%d %H:%M:%S %Z%z')
        except Exception as e:
            logger.error(f"Could not get local time for {destination_name} ({destination_timezone}): {e}")
            return None

    async def calculate_flight_arrival_details(
        self,
        departure_datetime_str: str, # ISO format e.g., "2025-10-20T10:00:00"
        departure_timezone: str,     # e.g., "America/Los_Angeles"
        arrival_timezone: str,       # e.g., "Asia/Tokyo"
        flight_duration_minutes: int
    ) -> Optional[Dict[str, str]]:
        """Calculates flight arrival time in both UTC and local arrival timezone."""
        try:
            # 1. Convert departure time to UTC
            # This requires knowing the UTC offset of departure_datetime_str in departure_timezone
            # The Time MCP's convert_time can be used: convert departure_datetime_str from departure_timezone to UTC

            # For simplicity, let's assume departure_datetime_str is naive and needs to be localized first.
            # A robust solution would use TimeMCP to get full datetime object with offset.
            # This is a conceptual example; actual implementation needs careful handling of naive vs. aware datetimes.

            # This is a simplified calculation. A robust version would use the TimeMCP for all conversions.
            # Assume departure_datetime_str is local to departure_timezone
            # Step 1: Get departure time as a full datetime object from TimeMCP to ensure correct DST
            departure_time_info = await self.time_mcp_client.convert_time(
                time_string=departure_datetime_str.split("T"), # "10:00:00"
                date_string=departure_datetime_str.split("T"),   # "2025-10-20"
                source_timezone=departure_timezone,
                target_timezone=departure_timezone # Convert to itself to get full object
            )
            departure_dt_aware = datetime.fromisoformat(departure_time_info['target']['datetime'])

            # Step 2: Calculate arrival time in UTC
            arrival_dt_utc = departure_dt_aware.astimezone(timezone.utc) + timedelta(minutes=flight_duration_minutes)

            # Step 3: Convert UTC arrival time to local arrival timezone using TimeMCP
            arrival_local_info = await self.time_mcp_client.convert_time(
                time_string=arrival_dt_utc.strftime("%H:%M:%S"),
                date_string=arrival_dt_utc.strftime("%Y-%m-%d"),
                source_timezone="UTC",
                target_timezone=arrival_timezone
            )

            return {
                "departure_local": departure_dt_aware.isoformat(),
                "departure_timezone": departure_timezone,
                "arrival_utc": arrival_dt_utc.isoformat(),
                "arrival_local": datetime.fromisoformat(arrival_local_info['target']['datetime']).isoformat(),
                "arrival_timezone": arrival_timezone,
                "flight_duration_minutes": flight_duration_minutes
            }
        except Exception as e:
            logger.error(f"Error calculating flight arrival: {e}")
            return None

    # ... other travel-specific time methods ...

# Factory function for the service
# def get_time_service() -> TripSageTimeService:
#    client = get_time_mcp_client()
#    return TripSageTimeService(client)
```

## 5. Agent Function Tools

The TimeMCPClient methods, decorated with @function_tool, are directly usable by AI agents. Additionally, higher-level tools can be created based on TripSageTimeService methods.

Example agent tools (can be defined in src/agents/tools/time_tools.py):

```python
# src/agents/tools/time_tools.py
# from ....mcp.time.client import get_time_mcp_client, get_time_service # Adjust import
# from agents import function_tool
# from pydantic import BaseModel, Field
# from typing import Optional, List

# time_mcp_client = get_time_mcp_client()
# time_service = get_time_service()

# @function_tool
# async def get_current_time_in_city(city_name: str, timezone_iana: str) -> str:
#     """Gets the current local time for a specified city and its IANA timezone."""
#     # params_model = time_mcp_client.get_current_time._openapi_parameters_model # Access Pydantic model
#     # validated_params = params_model(timezone=timezone_iana)
#     response = await time_mcp_client.get_current_time(timezone=timezone_iana)
#     if response.get("datetime"):
#         return f"The current time in {city_name} ({timezone_iana}) is {response['datetime']}."
#     return f"Could not retrieve time for {city_name}."

# @function_tool
# async def calculate_flight_arrival_time_tool(
#         departure_datetime_str: str,
#         departure_timezone: str,
#         arrival_timezone: str,
#         flight_duration_minutes: int
#     ) -> str:
#     """Calculates the local arrival time for a flight given departure details and duration."""
#     # ... (validation using Pydantic models) ...
#     arrival_details = await time_service.calculate_flight_arrival_details(
#         departure_datetime_str, departure_timezone, arrival_timezone, flight_duration_minutes
#     )
#     if arrival_details:
#         return f"The flight will arrive at {arrival_details['arrival_local']} local time in the destination ({arrival_details['arrival_timezone']})."
#     return "Could not calculate flight arrival time."

# ... other tools like find_meeting_times_tool, create_timezone_aware_itinerary_tool ...
```

## 6. Configuration

The Time MCP client relies on the centralized configuration system (AppSettings) for its endpoint:

```python
# From AppSettings in src/utils/config.py
# class TimeMCPServiceConfig(BaseModel):
#     endpoint: str = "http://localhost:3000" # Default if official server runs there
#     # api_key: Optional[SecretStr] = None # Usually not needed for Time MCP

# class MCPServerSettings(BaseModel):
#     time: TimeMCPServiceConfig = TimeMCPServiceConfig()
#     # ... other mcp configs

# class AppSettings(BaseSettings):
#     # ...
#     mcp_servers: MCPServerSettings = MCPServerSettings()
```

Ensure TIME_MCP_ENDPOINT (or TRIPSAGE_MCP_TIME_ENDPOINT depending on your naming convention in AppSettings) is set in your .env file if the Time MCP server runs on a non-default URL/port.

## 7. Testing

Client Tests (tests/mcp/time/test_time_mcp_client.py):
Mock the invoke_tool method of BaseMCPClient to test TimeMCPClient methods without a live Time MCP server.
Verify correct parameter formatting and response parsing.
Service Tests (tests/services/test_time_service.py):
Mock the TimeMCPClient to test the business logic within TripSageTimeService.
Integration Tests:
Run tests against a live instance of the official Time MCP server (can be started locally using the provided script). This verifies compatibility with the actual server.
Agent Tool Tests (tests/agents/tools/test_time_tools.py):
Mock the service or client layer to test the agent tool wrappers.

## 8. Conclusion

By integrating with the official Time MCP Server, TripSage gains standardized and reliable time and timezone functionalities. The TimeMCPClient and TripSageTimeService provide a clean, type-safe, and travel-domain-specific interface for the rest of the application, particularly for AI agents, to perform complex time-related calculations essential for travel planning.
