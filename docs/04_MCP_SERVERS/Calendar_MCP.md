# Calendar MCP Server Guide (Google Calendar Integration)

This document provides the comprehensive implementation guide and specification for the Calendar MCP Server within the TripSage AI Travel Planning System, focusing on integration with Google Calendar.

## 1. Overview

The Calendar MCP Server enables TripSage to interact with users' personal calendars, primarily Google Calendar. This integration allows users to:

- Add flights, accommodations, and activities from their TripSage itineraries directly to their Google Calendar.
- View existing calendar events to avoid scheduling conflicts during travel planning.
- Export entire TripSage itineraries as iCalendar (.ics) files for broader compatibility.

## 2. Architecture and Design Choices

- **Primary API Integration**: Google Calendar API.
- **MCP Framework**: FastMCP 2.0 (JavaScript/Node.js or Python).
- **Authentication**: OAuth 2.0 for secure access.
- **Token Management**: Secure storage and refresh for OAuth tokens.
- **ICS Generation**: For users who don’t use Google Calendar.

## 3. Google Calendar API Setup

1. Enable Calendar API in Google Cloud Console.
2. Configure OAuth Consent Screen, scopes, test users.
3. Create OAuth Client ID for web application (redirect URIs).
4. Store **Client ID** and **Client Secret** securely in environment variables.

## 4. Exposed MCP Tools

### 4.1. `authorize_calendar`

Initiates OAuth flow, returns an auth URL.

### 4.2. `handle_auth_callback`

Handles the Google callback, exchanges code for tokens, stores them.

### 4.3. `add_flight_to_calendar`

Adds a flight event. Includes airline, flight number, times, and a reminder.

### 4.4. `add_accommodation_to_calendar`

Adds accommodation check-in/out as calendar events.

### 4.5. `add_activity_to_calendar`

For activities with start/end times.

### 4.6. `create_travel_itinerary`

Adds multiple events (flights, accommodations, activities) in one go.

### 4.7. `get_calendar_events` (Optional)

Lists existing events in a given time range.

### 4.8. `export_trip_to_ical`

Generates an .ics file for an entire itinerary.

## 5. Core Service Implementations

### 5.1. `GoogleCalendarService`

- Uses Google OAuth2 client, calls calendar API (`events.insert`, etc.).
- Maps flight/accommodation/activity data to event objects.

### 5.2. `TokenService`

- Stores encrypted tokens in Supabase.
- Refreshes tokens when expired.

### 5.3. `ICSService`

- Uses an ICS library to generate iCalendar files from itinerary data.

## 6. Python Client (`CalendarMCPClient`)

```python
from typing import Dict, Any
from ..base_mcp_client import BaseMCPClient
from ...utils.config import settings
from agents import function_tool

class CalendarMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="calendar",
            endpoint=settings.mcp_servers.calendar.endpoint,
        )

    @function_tool
    async def add_flight_event_to_calendar(self, user_id: str, flight_details: Dict[str, Any], remind_before_hours: int = 3) -> Dict[str, Any]:
        payload = {
            "userId": user_id,
            "flightDetails": flight_details,
            "remind_before_hours": remind_before_hours
        }
        return await self.invoke_tool("add_flight_to_calendar", payload)
```

## 7. Agent Integration

- Agents prompt user for calendar authorization.
- Once authorized, events are added automatically or upon user request.

## 8. Security and OAuth Best Practices

- Use state parameter in OAuth flow.
- Encrypt tokens.
- Scope minimization.
- Token revocation handling.

## 9. Deployment

- Docker container for the MCP server.
- Requires environment variables for Google OAuth (`GOOGLE_CLIENT_ID`, etc.) and DB access.

This Calendar MCP server allows TripSage to seamlessly integrate itineraries with user calendars.
