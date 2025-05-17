# Calendar MCP Server Guide (Google Calendar Integration)

This document provides the comprehensive implementation guide and specification for the Calendar MCP Server within the TripSage AI Travel Planning System, focusing on integration with Google Calendar.

## 1. Overview

The Calendar MCP Server enables TripSage to interact with users' personal calendars, primarily Google Calendar. This integration allows users to:

- Add flights, accommodations, and activities from their TripSage itineraries directly to their Google Calendar.
- View existing calendar events to avoid scheduling conflicts during travel planning.
- Export entire TripSage itineraries as iCalendar (.ics) files for broader compatibility.

This functionality enhances the user experience by seamlessly incorporating travel plans into their daily schedules and providing timely reminders.

## 2. Architecture and Design Choices

- **Primary API Integration**: Google Calendar API.
  - **Rationale**: Widely used, robust API with comprehensive event management features, excellent SDKs, and a generous free tier suitable for personal use.
- **MCP Framework**: FastMCP 2.0 (JavaScript/Node.js version, as per original detailed docs, though a Python FastMCP 2.0 version would also align with general strategy).
  - **Rationale**: Standardization with TripSage's MCP ecosystem, ensuring compatibility with Claude Desktop and the OpenAI Agents SDK.
- **Authentication**: OAuth 2.0 for secure, user-delegated access to Google Calendar data.
- **Token Management**: Secure storage and refresh mechanisms for OAuth tokens.
- **ICS Generation**: Secondary capability to generate iCalendar files for users not using Google Calendar or for sharing.

## 3. Google Calendar API Setup (Prerequisites)

Before implementing the MCP server, the Google Calendar API must be configured in the Google Cloud Console:

1. **Create/Select Google Cloud Project**: (e.g., "TripSage-Personal-Calendar").
2. **Enable Google Calendar API**: In "APIs & Services" > "Library".
3. **Configure OAuth Consent Screen**:
    - User Type: "External".
    - App Name: "TripSage AI" (or user-defined for personal instances).
    - User Support Email: Your email.
    - Scopes:
      - `https://www.googleapis.com/auth/calendar` (Read/Write access to calendars)
      - `https://www.googleapis.com/auth/calendar.events` (Read/Write access to events)
    - Add Test Users: Your Google account(s) during development/testing.
4. **Create OAuth 2.0 Client ID**:
    - Application Type: "Web application".
    - Authorized Redirect URIs:
      - `http://localhost:PORT/auth/google/callback` (for local MCP server, replace `PORT` with actual, e.g., 3003 or 3004).
      - The callback URI exposed by your deployed TripSage application if it handles the final OAuth step.
    - Securely store the generated **Client ID** and **Client Secret**.

### Environment Variables for TripSage

```plaintext
# .env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
# This is the redirect URI registered in GCP and handled by your Calendar MCP or main app
GOOGLE_REDIRECT_URI=http://localhost:3004/auth/google/callback
CALENDAR_MCP_ENDPOINT=http://localhost:3004 # Endpoint of your Calendar MCP server
# ENCRYPTION_KEY=a_strong_key_for_encrypting_tokens (if tokens are stored by TripSage backend)
```

## 4. Exposed MCP Tools

The Calendar MCP Server, built with FastMCP 2.0, exposes the following tools:

### 4.1. `authorize_calendar`

- **Description**: Initiates the OAuth 2.0 flow by providing an authorization URL for Google Calendar.
- **Input Schema (Zod/Pydantic)**:

  ```javascript
  // Zod example
  z.object({
    userId: z
      .string()
      .describe("TripSage user identifier for token association."),
    // redirect_uri: z.string().url().describe("The URI the MCP server should use for its own callback handling if dynamic.")
  });
  ```

- **Output**: `{ authUrl: string, message: string }`
- **Handler Logic**:
  1. Generates a Google OAuth 2.0 authorization URL with the necessary scopes (`calendar`, `calendar.events`).
  2. Includes a `state` parameter (e.g., containing `userId` or a CSRF token) for security and context.

### 4.2. `handle_auth_callback`

- **Description**: Handles the callback from Google after user authorization, exchanges the authorization code for tokens.
- **Input Schema**:

  ```javascript
  z.object({
    userId: z.string().describe("User identifier from the state parameter."),
    code: z.string().describe("Authorization code from Google."),
    state: z.string().describe("State parameter for verification."),
  });
  ```

- **Output**: `{ success: boolean, message: string, userId?: string }`
- **Handler Logic**:
  1. Verifies the `state` parameter.
  2. Exchanges the `code` for an access token and a refresh token using Google API.
  3. Securely stores the tokens (e.g., encrypted in Supabase, associated with `userId`). The `TokenService` handles this.

### 4.3. `add_flight_to_calendar`

- **Description**: Adds a flight event to the user's primary Google Calendar.
- **Input Schema**:

  ```javascript
  z.object({
    userId: z.string(),
    flightDetails: z.object({
      airline: z.string(),
      flightNumber: z.string(),
      departureAirport: z.string(),
      arrivalAirport: z.string(),
      departureTime: z.string().datetime(), // ISO 8601 format
      arrivalTime: z.string().datetime(), // ISO 8601 format
      departureTimezone: z.string(), // IANA timezone, e.g., "America/New_York"
      arrivalTimezone: z.string(), // IANA timezone, e.g., "Europe/Paris"
      confirmationCode: z.string().optional(),
      // ... other relevant flight details
    }),
    remind_before_hours: z
      .number()
      .int()
      .min(0)
      .default(3)
      .describe("Reminder hours before departure"),
  });
  ```

- **Output**: `{ success: boolean, eventId?: string, calendarLink?: string, message: string }`
- **Handler Logic**: Uses `GoogleCalendarService` to create a new event with flight details, including appropriate summary, description, location (airports), and start/end times with timezones.

### 4.4. `add_accommodation_to_calendar`

- **Description**: Adds an accommodation booking (check-in/check-out) to the calendar.
- **Input Schema**:

  ```javascript
  z.object({
    userId: z.string(),
    accommodationDetails: z.object({
      propertyName: z.string(),
      address: z.string(),
      checkInDate: z.string().date(), // YYYY-MM-DD
      checkOutDate: z.string().date(), // YYYY-MM-DD
      checkInTime: z.string().optional(), // e.g., "15:00"
      checkOutTime: z.string().optional(), // e.g., "11:00"
      // ... other details
    }),
    // ...
  });
  ```

- **Output**: Similar to `add_flight_to_calendar`.
- **Handler Logic**: Creates an all-day event for the stay duration or specific check-in/check-out time events.

### 4.5. `add_activity_to_calendar`

- **Description**: Adds a planned activity or event to the calendar.
- **Input Schema**:

  ```javascript
  z.object({
    userId: z.string(),
    activityDetails: z.object({
      name: z.string(),
      location: z.string(),
      startTime: z.string().datetime(), // ISO 8601
      endTime: z.string().datetime(), // ISO 8601
      timezone: z.string(), // IANA timezone for the activity
      description: z.string().optional(),
      // ...
    }),
  });
  ```

- **Output**: Similar to `add_flight_to_calendar`.

### 4.6. `create_travel_itinerary`

- **Description**: Creates multiple calendar events for a full TripSage itinerary.
- **Input Schema**:

  ```javascript
  z.object({
    userId: z.string(),
    tripDetails: z.object({
      tripName: z.string(),
      tripId: z.string(), // TripSage trip ID
      flights: z.array(flightDetailsSchema).optional(), // Reuses flightDetails schema
      accommodations: z.array(accommodationDetailsSchema).optional(), // Reuses accommodationDetails schema
      activities: z.array(activityDetailsSchema).optional(), // Reuses activityDetails schema
    }),
  });
  ```

- **Output**: `{ success: boolean, createdEventIds: Record<string, string[]>, message: string }` (e.g., `createdEventIds: { flights: ["id1"], accommodations: ["id2"] }`)
- **Handler Logic**: Iterates through trip components and calls the respective `add_flight/accommodation/activity` logic, potentially in a batch request to Google Calendar API.

### 4.7. `get_calendar_events` (Optional, for conflict checking)

- **Description**: Lists events from the user's calendar for a given time range.
- **Input Schema**:

  ```javascript
  z.object({
    userId: z.string(),
    startDate: z.string().datetime(),
    endDate: z.string().datetime(),
    maxResults: z.number().int().default(10),
  });
  ```

- **Output**: `{ events: CalendarEvent[] }`

### 4.8. `export_trip_to_ical` (was `exportCalendarEvents`)

- **Description**: Exports a TripSage trip itinerary as an iCalendar (.ics) file.
- **Input Schema**:

  ```javascript
  z.object({
    userId: z.string(), // Needed if events are fetched from user's Google Calendar
    tripId: z.string().describe("TripSage trip identifier to export"),
    // Or alternatively, pass the full trip data directly
    // tripData: tripDetailsSchema
  });
  ```

- **Output**: `{ icalContent: string, fileName: string }`
- **Handler Logic**:
  1. Fetches trip details from Supabase using `tripId`.
  2. Uses an ICS generation library (e.g., `ics` for Node.js) to construct the iCalendar data from the trip components.
  3. Does _not_ necessarily require Google Calendar API access if exporting from TripSage data. If exporting _from_ Google Calendar, then `userId` and token access are needed.

## 5. Core Service Implementations

### 5.1. `GoogleCalendarService` (`google_calendar_service.ts` or `.js`)

This service encapsulates all direct interactions with the Google Calendar API.

- **OAuth2 Client Management**: Initializes `google.auth.OAuth2` client.
- **Token Handling**: Uses `TokenService` to get/refresh user tokens. Sets credentials on the OAuth2 client.
- **API Calls**: Uses `googleapis.calendar('v3')` to interact with calendar endpoints (events.insert, events.list, etc.).
- **Event Formatting**: Contains logic to map TripSage `flightDetails`, `accommodationDetails`, etc., into Google Calendar event resource objects (summary, description, start, end, location, reminders, timezones).
  - **Flights**: Summary like "Flight UA123 SFO-JFK". Description includes airline, flight number, terminals, confirmation.
  - **Accommodations**: Summary like "Check-in: Hotel XYZ". All-day events for stay duration. Description includes address, confirmation.
  - **Activities**: Summary is activity name. Description includes details.
- **Timezone Handling**: Ensures all `dateTime` fields sent to Google include the correct `timeZone` property. Leverages the Time MCP for complex timezone calculations if needed before creating the event.

### 5.2. `TokenService` (`token_service.ts` or `.js`)

- **Responsibilities**: Securely storing, retrieving, and refreshing OAuth tokens.
- **Storage**: Uses Supabase (a dedicated `auth_tokens` table) to store encrypted access and refresh tokens per user, per provider (Google Calendar).
  - Table columns: `user_id`, `provider` (e.g., "google_calendar"), `encrypted_access_token`, `encrypted_refresh_token`, `expiry_date`, `scopes`.
- **Encryption**: Uses a strong encryption key (from `ENCRYPTION_KEY` env var) to encrypt tokens before database storage.
- **Refresh Logic**: Implements logic to use the refresh token to get a new access token when the current one is expired or about to expire. Updates the stored tokens.

### 5.3. `ICSService` (`ics_service.ts` or `.js`) (for `export_trip_to_ical`)

- Uses a library like `ics` (npm) to generate iCalendar formatted strings.
- Maps TripSage itinerary components to VEVENT properties.

## 6. Python Client (`src/mcp/calendar/client.py`)

A Python client using `BaseMCPClient` to interact with the (JavaScript/Node.js) Calendar MCP Server.

```python
# src/mcp/calendar/client.py (Simplified Snippet)
from typing import Dict, Any, List, Optional
from ..base_mcp_client import BaseMCPClient
from ...utils.config import settings
from agents import function_tool

class CalendarMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="calendar",
            endpoint=settings.mcp_servers.calendar.endpoint,
            # ...
        )

    @function_tool
    async def add_flight_event_to_calendar(self, user_id: str, flight_details: Dict[str, Any], remind_before_hours: int = 3) -> Dict[str, Any]:
        """Adds a flight event to the user's Google Calendar."""
        # Validate flight_details with a Pydantic model
        payload = {
            "userId": user_id,
            "flightDetails": flight_details,
            "remind_before_hours": remind_before_hours
        }
        return await self.invoke_tool("add_flight_to_calendar", payload)

    # ... other methods for add_accommodation, add_activity, create_travel_itinerary, authorize_calendar etc.
```

## 7. Agent Integration

The `CalendarMCPClient` tools are registered with the Itinerary Agent and Travel Planning Agent.

- After a booking is confirmed (flight/hotel) or an activity is added to the plan, the agent can prompt the user if they'd like to add it to their calendar.
- If the user hasn't authorized calendar access, the agent initiates the `authorize_calendar` flow.
- The `create_travel_itinerary` tool can be used to add an entire trip's worth of events in one go.

## 8. Security and OAuth Best Practices

- **State Parameter**: Use a `state` parameter in the OAuth flow to prevent CSRF attacks. The `state` should be generated by TripSage, sent to Google, and then verified when Google calls back. It can include the `userId` for context.
- **Token Encryption**: Encrypt OAuth tokens (especially refresh tokens) at rest in the database.
- **Scope Minimization**: Only request the necessary scopes (`calendar` and `calendar.events`).
- **Secure Redirect URI**: Ensure `GOOGLE_REDIRECT_URI` is HTTPS in production and precisely matches what's configured in Google Cloud Console.
- **Token Revocation**: Provide a mechanism for users to disconnect their Google Calendar and revoke TripSage's access (this would involve calling Google's token revocation endpoint and deleting stored tokens).

## 9. Deployment

- The Calendar MCP Server is a Node.js application, containerized using Docker.
- It requires environment variables for `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, and `ENCRYPTION_KEY`.
- It needs network access to Google APIs and the Supabase database (for token storage).

This Calendar MCP server provides a robust and secure way for TripSage to integrate with Google Calendar, enhancing the utility of planned itineraries.
