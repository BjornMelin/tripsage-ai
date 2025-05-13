# Google Calendar MCP Implementation Guide

This document provides a comprehensive implementation guide for the Google Calendar MCP integration in the TripSage system, which allows for itinerary scheduling and calendar management.

## Table of Contents

- [Google Calendar MCP Implementation Guide](#google-calendar-mcp-implementation-guide)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
  - [Implementation Details](#implementation-details)
    - [Calendar MCP Client](#calendar-mcp-client)
    - [Calendar Service](#calendar-service)
    - [Agent Tools](#agent-tools)
    - [OAuth Flow](#oauth-flow)
  - [Setting Up Google Calendar Integration](#setting-up-google-calendar-integration)
    - [Google Cloud Project Setup](#google-cloud-project-setup)
    - [OAuth Consent Screen](#oauth-consent-screen)
    - [OAuth Credentials](#oauth-credentials)
    - [Environment Variables](#environment-variables)
  - [Deploying the Google Calendar MCP Server](#deploying-the-google-calendar-mcp-server)
    - [Installation](#installation)
    - [Configuration](#configuration)
    - [Running the Server](#running-the-server)
  - [Itinerary-to-Calendar Mapping](#itinerary-to-calendar-mapping)
    - [Mapping Logic](#mapping-logic)
    - [Event Type Customization](#event-type-customization)
  - [Testing the Integration](#testing-the-integration)
    - [Unit Testing](#unit-testing)
    - [Integration Testing](#integration-testing)
  - [Troubleshooting](#troubleshooting)
    - [Common Errors](#common-errors)
    - [OAuth Issues](#oauth-issues)
    - [MCP Server Issues](#mcp-server-issues)

## Overview

The Google Calendar MCP integration allows TripSage to:

1. List, search, create, update, and delete events in a user's Google Calendar
2. Convert travel itineraries into calendar events
3. Handle OAuth authentication with Google Calendar API
4. Provide agent-facing tools to work with Google Calendar

This integration leverages the `nspady/google-calendar-mcp` Model Context Protocol server, which provides a standardized interface to the Google Calendar API.

## Prerequisites

- Google Cloud Project with Calendar API enabled
- OAuth 2.0 Client ID and Secret
- Node.js 14+ for running the Google Calendar MCP server
- Python 3.9+ environment with `uv` for package management
- FastMCP 2.0 for MCP client implementation
- Proper configuration in environment variables or config files

## Implementation Details

### Calendar MCP Client

The `CalendarMCPClient` class in `src/mcp/calendar/client.py` provides a client for interacting with the Google Calendar MCP server. It inherits from `FastMCPClient` and provides methods for:

- `get_calendars()` - List available calendars
- `get_events()` - List events from a calendar
- `search_events()` - Search for events matching a query
- `create_event()` - Create a new event
- `update_event()` - Update an existing event
- `delete_event()` - Delete an event

Each method validates input parameters using Pydantic models, calls the appropriate MCP tool, and validates the response.

### Calendar Service

The `CalendarService` class provides higher-level functionality for working with Google Calendar, including:

- `create_itinerary_events()` - Convert TripSage itinerary items into calendar events

This service uses the `CalendarMCPClient` to interact with the Google Calendar MCP server but adds TripSage-specific logic for mapping itinerary data to calendar events.

### Agent Tools

The agent tools in `src/agents/calendar_tools.py` provide a set of `@function_tool` decorated functions that agents can use to interact with Google Calendar:

- `list_calendars_tool()` - List all available calendars
- `list_events_tool()` - List events from a calendar
- `search_events_tool()` - Search for events matching a query
- `create_event_tool()` - Create a new event
- `update_event_tool()` - Update an existing event
- `delete_event_tool()` - Delete an event
- `create_itinerary_events_tool()` - Convert TripSage itinerary items into calendar events

These tools wrap the `CalendarMCPClient` and `CalendarService` methods, adding error handling and formatting the responses for agent consumption.

### OAuth Flow

The Google Calendar MCP server handles OAuth authentication with Google Calendar. This process requires:

1. Setting up a Google Cloud Project with the Calendar API enabled
2. Creating OAuth credentials (Client ID and Secret)
3. Running the MCP server with these credentials
4. A user going through the OAuth flow to grant access to their calendar

The `nspady/google-calendar-mcp` server handles token storage and refresh. TripSage stores the Client ID and Secret in the `CalendarMCPConfig` settings class.

## Setting Up Google Calendar Integration

### Google Cloud Project Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Library"
4. Search for "Google Calendar API" and enable it
5. Navigate to "APIs & Services" > "OAuth consent screen"
6. Configure the OAuth consent screen:
   - Select "External" user type (for general use)
   - Enter app name, user support email, and developer contact information
   - Add scopes for Google Calendar API (`https://www.googleapis.com/auth/calendar` and `https://www.googleapis.com/auth/calendar.events`)
   - Add test users (if in testing mode)

### OAuth Consent Screen

Configure the OAuth consent screen with the following information:

- **App name**: "TripSage AI"
- **User support email**: Your support email
- **App logo**: TripSage logo
- **App domain**: Your domain
- **Authorized domains**: Your domain
- **Developer contact information**: Your contact email

### OAuth Credentials

1. Navigate to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application" as the application type
4. Add an authorized redirect URI for the Google Calendar MCP server (e.g., `http://localhost:3003/auth/callback`)
5. Click "Create" and note the Client ID and Client Secret

### Environment Variables

Add the following environment variables to your `.env` file:

```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3003/auth/callback
CALENDAR_MCP_ENDPOINT=http://localhost:3003
```

## Deploying the Google Calendar MCP Server

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nspady/google-calendar-mcp.git
   cd google-calendar-mcp
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy the OAuth keys template:
   ```bash
   cp gcp-oauth.keys.example.json gcp-oauth.keys.json
   ```

4. Edit `gcp-oauth.keys.json` and add your Client ID and Secret.

### Configuration

The `scripts/start_calendar_mcp.sh` script automates the setup and configuration process. It:

1. Clones or updates the Google Calendar MCP repository
2. Installs dependencies
3. Creates the OAuth keys file if it doesn't exist
4. Builds the TypeScript code
5. Starts the server

### Running the Server

Execute the script to start the server:

```bash
./scripts/start_calendar_mcp.sh
```

The server will start on port 3003 by default. You can change this by setting the `MCP_PORT` environment variable.

## Itinerary-to-Calendar Mapping

### Mapping Logic

The `_map_itinerary_item_to_event` method in `CalendarService` maps TripSage itinerary items to Google Calendar events with the following logic:

1. Convert basic properties (title, description, location)
2. Add trip name to the description
3. Format start and end times based on whether it's an all-day event
4. Add custom reminders based on event type
5. Add event-specific information based on the item type (flight, accommodation, etc.)
6. Add a note indicating the event was created by TripSage

### Event Type Customization

Different itinerary item types have specialized handling:

- **Flights**: Add flight number to title, flight details to description, reminder 3 hours before
- **Accommodations**: Add check-in/out details, reminder 1 day before
- **Activities**: Use default reminder configuration

## Testing the Integration

### Unit Testing

The `tests/mcp/calendar/test_calendar_client.py` file contains unit tests for the `CalendarMCPClient` class, covering all methods with mock responses.

The `tests/mcp/calendar/test_calendar_models.py` file contains unit tests for the Pydantic models used in the calendar integration.

The `tests/agents/test_calendar_tools.py` file contains unit tests for the agent tools, mocking the client and service methods.

### Integration Testing

For integration testing:

1. Set up test Google Calendar credentials
2. Run the Google Calendar MCP server
3. Create test calendars and events
4. Verify that TripSage can list, create, update, and delete events
5. Verify that itinerary items can be converted to calendar events

## Troubleshooting

### Common Errors

- **"Invalid parameters"**: Check that all required parameters are provided and in the correct format
- **"Failed to get calendars"**: Check that the MCP server is running and the OAuth token is valid
- **"HTTPError"**: Check server logs for details on the HTTP error
- **"ValidationError"**: Check that input data matches the expected schema

### OAuth Issues

- **Invalid token**: Run `npm run auth` in the Google Calendar MCP directory to re-authenticate
- **Token expired**: The MCP server should refresh tokens automatically, but may need re-authentication if the refresh token expires
- **Invalid client ID or secret**: Verify that the credentials in `gcp-oauth.keys.json` match those in the Google Cloud Console

### MCP Server Issues

- **Server not starting**: Check for errors in the console, ensure Node.js is installed, and dependencies are installed
- **Connection refused**: Ensure the server is running and the endpoint is correct
- **Timeout**: Check the server logs, increase the client timeout, and ensure the server has enough resources