# Google Calendar Integration Guide

This document provides comprehensive instructions for integrating Google Calendar API into TripSage to enable travel itinerary management. This integration allows users to add their travel plans to their personal calendars with complete details and timely reminders.

## Overview

Google Calendar API is a powerful tool that allows applications to interact with users' calendars. Key features include:

- Full event management capabilities
- OAuth 2.0 authentication flow
- Comprehensive support for travel-specific events
- Rich metadata support
- Customizable notifications and reminders
- Support for recurring events and all-day events
- Excellent documentation and SDKs
- High availability and reliability

The free tier offers:

- 1 million API requests per day
- Generous quota limits for personal usage
- No cost for individual users
- No infrastructure requirements

## Setup Instructions

### 1. Create a Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "TripSage-Personal")
3. Note your Project ID for future reference

### 2. Enable the Google Calendar API

1. In your Google Cloud project, navigate to "APIs & Services" > "Library"
2. Search for "Google Calendar API" and select it
3. Click "Enable" to activate the API for your project

### 3. Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "External" user type (since this is for personal use)
3. Fill in the required application information:
   - App name: "TripSage"
   - User support email: Your email address
   - Developer contact information: Your email address
4. Add the following scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/calendar.events`
5. Add your email address as a test user
6. Complete the registration process

### 4. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" and select "OAuth client ID"
3. Select "Web application" as the application type
4. Add the following authorized redirect URIs:
   - `http://localhost:3000/auth/google/callback` (for local development)
   - Any other URIs where you'll host your application
5. Click "Create"
6. Save the Client ID and Client Secret that are generated

### 5. Configure TripSage

1. Create or edit the `.env` file in your TripSage project root
2. Add your Google Cloud credentials:

   ```plaintext
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
   ```

3. Save the file and restart your TripSage application

## Implementation Guide

### 1. FastMCP 2.0 Calendar MCP Server Implementation

Create a file `src/mcp/calendar/server.js`:

```javascript
// server.js
import { FastMCP } from "fastmcp";
import {
  authorizeCalendar,
  getCalendarEvents,
  addFlightToCalendar,
  addAccommodationToCalendar,
  addActivityToCalendar,
  createTravelItinerary,
  exportCalendarEvents,
} from "./tools";

// Create FastMCP 2.0 server
const server = new FastMCP({
  name: "calendar-mcp",
  version: "1.0.0",
  description: "Calendar MCP Server for TripSage",
});

// Register tools
server.registerTool(authorizeCalendar);
server.registerTool(getCalendarEvents);
server.registerTool(addFlightToCalendar);
server.registerTool(addAccommodationToCalendar);
server.registerTool(addActivityToCalendar);
server.registerTool(createTravelItinerary);
server.registerTool(exportCalendarEvents);

// Start the server
server.start();
```

Create the tools file `src/mcp/calendar/tools/index.js`:

```javascript
// tools/index.js
import { z } from "zod";
import { createTool } from "fastmcp";
import { GoogleCalendarService } from "../services/google-calendar-service";

const googleCalendarService = new GoogleCalendarService();

// Tool for calendar authorization
export const authorizeCalendar = createTool({
  name: "authorize_calendar",
  description: "Get Google Calendar authorization URL for user",
  input: z.object({
    userId: z.string().describe("User identifier"),
  }),
  handler: async ({ input, context }) => {
    try {
      const authUrl = googleCalendarService.getAuthUrl(input.userId);
      return { authUrl };
    } catch (error) {
      throw new Error(`Failed to get authorization URL: ${error.message}`);
    }
  },
});

// Tool for getting calendar events
export const getCalendarEvents = createTool({
  name: "get_calendar_events",
  description: "Get upcoming calendar events for a user",
  input: z.object({
    userId: z.string().describe("User identifier"),
    maxResults: z
      .number()
      .default(10)
      .describe("Maximum number of events to return"),
  }),
  handler: async ({ input, context }) => {
    try {
      const events = await googleCalendarService.listUpcomingEvents(
        input.userId,
        input.maxResults
      );
      return { events };
    } catch (error) {
      throw new Error(`Failed to list calendar events: ${error.message}`);
    }
  },
});

// Tool for adding flights to calendar
export const addFlightToCalendar = createTool({
  name: "add_flight_to_calendar",
  description: "Add flight to user's calendar",
  input: z.object({
    userId: z.string().describe("User identifier"),
    flightDetails: z
      .object({
        airline: z.string().describe("Airline name"),
        flightNumber: z.string().describe("Flight number"),
        departureAirport: z.string().describe("Departure airport code"),
        arrivalAirport: z.string().describe("Arrival airport code"),
        departureTime: z.string().describe("Departure time in ISO format"),
        arrivalTime: z.string().describe("Arrival time in ISO format"),
        departureTerminal: z.string().optional().describe("Departure terminal"),
        arrivalTerminal: z.string().optional().describe("Arrival terminal"),
        confirmationCode: z
          .string()
          .optional()
          .describe("Booking confirmation code"),
        status: z.string().optional().describe("Flight status"),
        seat: z.string().optional().describe("Seat assignment"),
      })
      .describe("Flight booking details"),
  }),
  handler: async ({ input, context }) => {
    try {
      const event = await googleCalendarService.addFlightToCalendar(
        input.userId,
        input.flightDetails
      );
      return { event };
    } catch (error) {
      throw new Error(`Failed to add flight to calendar: ${error.message}`);
    }
  },
});

// Tool for adding accommodations to calendar
export const addAccommodationToCalendar = createTool({
  name: "add_accommodation_to_calendar",
  description: "Add accommodation to user's calendar",
  input: z.object({
    userId: z.string().describe("User identifier"),
    accommodationDetails: z
      .object({
        propertyName: z.string().describe("Property name"),
        address: z.string().describe("Property address"),
        checkInDate: z.string().describe("Check-in date in ISO format"),
        checkOutDate: z.string().describe("Check-out date in ISO format"),
        checkInTime: z.string().optional().describe("Check-in time"),
        checkOutTime: z.string().optional().describe("Check-out time"),
        confirmationCode: z
          .string()
          .optional()
          .describe("Booking confirmation code"),
        roomType: z.string().optional().describe("Room or unit type"),
        guests: z.number().optional().describe("Number of guests"),
      })
      .describe("Accommodation booking details"),
  }),
  handler: async ({ input, context }) => {
    try {
      const event = await googleCalendarService.addAccommodationToCalendar(
        input.userId,
        input.accommodationDetails
      );
      return { event };
    } catch (error) {
      throw new Error(
        `Failed to add accommodation to calendar: ${error.message}`
      );
    }
  },
});

// Tool for adding activities to calendar
export const addActivityToCalendar = createTool({
  name: "add_activity_to_calendar",
  description: "Add activity to user's calendar",
  input: z.object({
    userId: z.string().describe("User identifier"),
    activityDetails: z
      .object({
        name: z.string().describe("Activity name"),
        location: z.string().describe("Activity location"),
        startTime: z.string().describe("Start time in ISO format"),
        endTime: z.string().describe("End time in ISO format"),
        description: z.string().optional().describe("Activity description"),
        confirmationCode: z
          .string()
          .optional()
          .describe("Booking confirmation code"),
        participants: z.number().optional().describe("Number of participants"),
        additionalInfo: z
          .string()
          .optional()
          .describe("Additional information"),
      })
      .describe("Activity details"),
  }),
  handler: async ({ input, context }) => {
    try {
      const event = await googleCalendarService.addActivityToCalendar(
        input.userId,
        input.activityDetails
      );
      return { event };
    } catch (error) {
      throw new Error(`Failed to add activity to calendar: ${error.message}`);
    }
  },
});

// Tool for creating complete travel itinerary
export const createTravelItinerary = createTool({
  name: "create_travel_itinerary",
  description: "Create complete travel itinerary in calendar",
  input: z.object({
    userId: z.string().describe("User identifier"),
    tripDetails: z
      .object({
        tripId: z.string().describe("Trip identifier"),
        flights: z
          .array(z.any())
          .optional()
          .describe("Array of flight details"),
        accommodations: z
          .array(z.any())
          .optional()
          .describe("Array of accommodation details"),
        activities: z
          .array(z.any())
          .optional()
          .describe("Array of activity details"),
      })
      .describe("Complete trip details"),
  }),
  handler: async ({ input, context }) => {
    try {
      const result = await googleCalendarService.createTravelItinerary(
        input.userId,
        input.tripDetails
      );
      return result;
    } catch (error) {
      throw new Error(`Failed to create travel itinerary: ${error.message}`);
    }
  },
});

// Tool for exporting calendar events
export const exportCalendarEvents = createTool({
  name: "export_calendar_events",
  description: "Export calendar events for a trip as iCal",
  input: z.object({
    userId: z.string().describe("User identifier"),
    tripId: z.string().describe("Trip identifier"),
  }),
  handler: async ({ input, context }) => {
    try {
      const icalContent = await googleCalendarService.exportTripAsICalendar(
        input.userId,
        input.tripId
      );
      return { icalContent };
    } catch (error) {
      throw new Error(`Failed to export calendar events: ${error.message}`);
    }
  },
});
```

### 2. Python Client Implementation

Create a file `src/mcp/calendar/client.py`:

```python
from agents import function_tool
from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class CalendarMCPClient(BaseMCPClient):
    """Client for the Calendar MCP Server."""

    def __init__(self):
        """Initialize the Calendar MCP client."""
        super().__init__(server_name="calendar")
        logger.info("Initialized Calendar MCP Client")

    @function_tool
    async def authorize_calendar(self, user_id: str) -> dict:
        """Get Google Calendar authorization URL for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with authorization URL
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "authorize_calendar",
                {
                    "userId": user_id
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting calendar authorization URL: {str(e)}")
            return {
                "error": f"Failed to get calendar authorization URL: {str(e)}"
            }

    @function_tool
    async def add_flight_to_calendar(
        self,
        user_id: str,
        flight_details: dict
    ) -> dict:
        """Add flight to user's calendar.

        Args:
            user_id: User identifier
            flight_details: Dictionary with flight booking details

        Returns:
            Dictionary with created calendar event details
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "add_flight_to_calendar",
                {
                    "userId": user_id,
                    "flightDetails": flight_details
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error adding flight to calendar: {str(e)}")
            return {
                "error": f"Failed to add flight to calendar: {str(e)}"
            }

    @function_tool
    async def add_accommodation_to_calendar(
        self,
        user_id: str,
        accommodation_details: dict
    ) -> dict:
        """Add accommodation to user's calendar.

        Args:
            user_id: User identifier
            accommodation_details: Dictionary with accommodation booking details

        Returns:
            Dictionary with created calendar event details
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "add_accommodation_to_calendar",
                {
                    "userId": user_id,
                    "accommodationDetails": accommodation_details
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error adding accommodation to calendar: {str(e)}")
            return {
                "error": f"Failed to add accommodation to calendar: {str(e)}"
            }

    @function_tool
    async def add_activity_to_calendar(
        self,
        user_id: str,
        activity_details: dict
    ) -> dict:
        """Add activity to user's calendar.

        Args:
            user_id: User identifier
            activity_details: Dictionary with activity details

        Returns:
            Dictionary with created calendar event details
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "add_activity_to_calendar",
                {
                    "userId": user_id,
                    "activityDetails": activity_details
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error adding activity to calendar: {str(e)}")
            return {
                "error": f"Failed to add activity to calendar: {str(e)}"
            }

    @function_tool
    async def create_travel_itinerary(
        self,
        user_id: str,
        trip_details: dict
    ) -> dict:
        """Create complete travel itinerary in calendar.

        Args:
            user_id: User identifier
            trip_details: Dictionary with complete trip details

        Returns:
            Dictionary with created calendar events details
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "create_travel_itinerary",
                {
                    "userId": user_id,
                    "tripDetails": trip_details
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error creating travel itinerary: {str(e)}")
            return {
                "error": f"Failed to create travel itinerary: {str(e)}"
            }
```

### 3. OpenAI Agents SDK Integration

Update `mcp_servers/openai_agents_config.js` to add the Calendar MCP server:

```javascript
// mcp_servers/openai_agents_config.js
module.exports = {
  mcpServers: {
    // Existing MCP servers...

    // Calendar MCP Server
    calendar: {
      command: "node",
      args: ["./src/mcp/calendar/server.js"],
      env: {
        GOOGLE_CLIENT_ID: "${GOOGLE_CLIENT_ID}",
        GOOGLE_CLIENT_SECRET: "${GOOGLE_CLIENT_SECRET}",
        GOOGLE_REDIRECT_URI: "${GOOGLE_REDIRECT_URI}",
      },
    },
  },
};
```

### 4. Claude Desktop Integration

For Claude Desktop integration, add the Calendar MCP Server to the Claude Desktop configuration:

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "calendar": {
      "command": "node",
      "args": ["./src/mcp/calendar/server.js"],
      "env": {
        "GOOGLE_CLIENT_ID": "${GOOGLE_CLIENT_ID}",
        "GOOGLE_CLIENT_SECRET": "${GOOGLE_CLIENT_SECRET}",
        "GOOGLE_REDIRECT_URI": "${GOOGLE_REDIRECT_URI}"
      }
    }
  }
}
```

### 5. Agent Integration

The Calendar MCP client can be integrated into the TripSage agent architecture to provide calendar functionality:

```python
# src/agents/travel_agent.py
from src.mcp.calendar.client import CalendarMCPClient
from src.mcp.flights.client import FlightsMCPClient
from src.mcp.time.client import TimeMCPClient
from src.mcp.openai_agents_integration import create_agent_with_mcp_servers

async def create_travel_agent():
    """Create a travel agent with flight search and calendar capabilities."""
    # Create MCP clients
    flights_client = FlightsMCPClient()
    calendar_client = CalendarMCPClient()
    time_client = TimeMCPClient()

    # Create agent with MCP servers
    agent = await create_agent_with_mcp_servers(
        name="TripSage Travel Agent",
        instructions="""You are a travel planning assistant that helps users find flights,
        accommodations, and activities. Use the appropriate tools to search for flights,
        add events to calendars, convert time between timezones, and provide comprehensive travel plans.""",
        server_names=["flights", "calendar", "time"],
        tools=[
            flights_client.search_flights,
            flights_client.search_multi_city,
            calendar_client.add_flight_to_calendar,
            calendar_client.add_accommodation_to_calendar,
            calendar_client.add_activity_to_calendar,
            calendar_client.create_travel_itinerary,
            time_client.get_current_time,
            time_client.convert_time
        ],
        model="gpt-4o"
    )

    return agent
```

## OAuth Authentication Flow

The Google Calendar integration uses OAuth 2.0 for secure authentication. Here's how the flow works:

### 1. Authorization Request

1. User initiates calendar integration (e.g., "Add my flight to calendar")
2. TripSage checks if the user has already authorized Google Calendar
3. If not authorized, TripSage generates an authorization URL using the Google OAuth2 client
4. TripSage presents the URL to the user with instructions to authorize

### 2. User Authorization

1. User clicks the authorization link and is directed to Google's OAuth consent screen
2. Google presents the requested scopes (calendar.readonly, calendar.events)
3. User approves the authorization request
4. Google redirects back to TripSage's redirect URI with an authorization code

### 3. Token Exchange

1. TripSage receives the authorization code from the redirect
2. TripSage exchanges the code for access and refresh tokens
3. TripSage securely stores the tokens associated with the user account
4. TripSage confirms successful connection to the user

### 4. Token Management

1. When making API calls, TripSage checks if the access token is expired
2. If expired, TripSage uses the refresh token to obtain a new access token
3. If refresh fails, TripSage prompts the user to re-authorize
4. Tokens are securely stored and never exposed to client-side code

## Security Best Practices

### Personal API Key Security

1. **Environment Variables**:

   - Store sensitive credentials in environment variables
   - Never commit .env files to source control
   - Use different credentials for development and production

2. **Token Storage**:

   - Store OAuth tokens in a secure database
   - Never store tokens in client-side storage (localStorage, cookies)
   - Encrypt tokens at rest if possible

3. **Scope Limitation**:

   - Request only the calendar permissions you need
   - Use read-only scopes when write access isn't necessary

4. **CSRF Protection**:

   - Implement state parameter validation in OAuth flow
   - Generate and verify unique state tokens for each auth request

5. **Regular Cleanup**:
   - Implement token revocation when users disconnect
   - Set up database cleanup for expired tokens

### Cost Optimization for Personal Usage

Google Calendar API is free for personal use, but implementing these best practices ensures efficient usage:

1. **Caching**:

   - Cache calendar data when appropriate
   - Avoid redundant API calls for the same information
   - Implement a cache invalidation strategy

2. **Batch Requests**:

   - Use the Google API batch request feature to combine multiple operations
   - Create complete itineraries in a single batch request

3. **Rate Limiting**:

   - Implement client-side rate limiting to prevent quota exhaustion
   - Add exponential backoff for retries on API failures

4. **Efficient Data Retrieval**:
   - Request only the data fields you need
   - Use pagination for large event lists
   - Filter events by date range to reduce response size

## Testing and Verification

### Unit Tests

Create a file `src/mcp/calendar/tests/test_client.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta

from src.mcp.calendar.client import CalendarMCPClient

@pytest.fixture
def calendar_client():
    """Create a calendar client for testing."""
    return CalendarMCPClient()

@pytest.fixture
def mock_server():
    """Mock MCP server."""
    server_mock = AsyncMock()
    server_mock.invoke_tool = AsyncMock()
    return server_mock

@pytest.mark.asyncio
async def test_add_flight_to_calendar(calendar_client, mock_server):
    """Test add_flight_to_calendar method."""
    # Setup mock
    with patch.object(calendar_client, 'get_server', return_value=mock_server):
        # Create mock response
        mock_response = {
            "event": {
                "id": "event_12345",
                "summary": "Flight: AA 123",
                "status": "confirmed"
            }
        }

        mock_server.invoke_tool.return_value = mock_response

        # Get tomorrow's date
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        six_hours_later = (date.today() + timedelta(days=1, hours=6)).strftime("%Y-%m-%dT%H:%M:%S")

        # Test data
        flight_details = {
            "airline": "American Airlines",
            "flightNumber": "123",
            "departureAirport": "LAX",
            "arrivalAirport": "JFK",
            "departureTime": tomorrow,
            "arrivalTime": six_hours_later,
            "departureTerminal": "T4",
            "arrivalTerminal": "T2",
            "confirmationCode": "ABC123"
        }

        # Call method
        result = await calendar_client.add_flight_to_calendar(
            user_id="test_user_123",
            flight_details=flight_details
        )

        # Assertions
        assert result == mock_response
        mock_server.invoke_tool.assert_called_once()
        args, kwargs = mock_server.invoke_tool.call_args

        # Verify tool name
        assert args[0] == "add_flight_to_calendar"

        # Verify parameters
        assert args[1]["userId"] == "test_user_123"
        assert args[1]["flightDetails"]["airline"] == "American Airlines"
        assert args[1]["flightDetails"]["flightNumber"] == "123"
```

### Integration Testing

Test the following scenarios:

1. **Authorization Flow**:

   - Test the OAuth authorization URL generation
   - Test the OAuth callback handling
   - Verify token storage and retrieval
   - Test token refresh logic

2. **Event Creation and Management**:
   - Test adding flights to calendar
   - Test adding accommodations to calendar
   - Test adding activities to calendar
   - Test creating complete itineraries
   - Test updating and deleting events
   - Test calendar export functionality

## Integration with TripSage Components

The calendar integration works seamlessly with other TripSage features:

1. **Flight Booking**: After booking a flight, offer to add it to the user's calendar
2. **Accommodation Booking**: Add hotel stays as all-day events with check-in/out details
3. **Activity Planning**: Sync planned activities with appropriate reminders
4. **Weather Integration**: Enhance calendar events with weather forecasts
5. **Itinerary Management**: Provide a comprehensive calendar view of the entire trip

## Implementation Checklist

- [ ] Create Google Cloud project and enable Calendar API
- [ ] Configure OAuth consent screen and create credentials
- [ ] Set up environment variables for API keys
- [ ] Implement FastMCP 2.0 Calendar MCP server
- [ ] Create OAuth authentication flow
- [ ] Implement token storage and refresh mechanism
- [ ] Add calendar event creation methods for different travel items
- [ ] Create Python client for Calendar MCP server
- [ ] Configure OpenAI Agents SDK and Claude Desktop integration
- [ ] Implement error handling and security measures
- [ ] Write unit and integration tests
- [ ] Document the integration thoroughly

By following this implementation guide, you'll have a robust Google Calendar integration using FastMCP 2.0 that enhances the travel planning experience with comprehensive itinerary management while supporting personal use with individual Google accounts.
