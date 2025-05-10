# Calendar MCP Server Implementation

This document provides the detailed implementation specification for the Calendar MCP Server in TripSage.

## Overview

The Calendar MCP Server provides integration with popular calendar services, primarily Google Calendar, enabling users to add their travel itineraries to their personal calendars. The server handles OAuth authentication, event creation, and itinerary synchronization, ensuring travel plans are properly organized and accessible.

## MCP Tools Exposed

```typescript
// MCP Tool Definitions
{
  "name": "mcp__calendar__authorize",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID for token management"},
    "redirect_uri": {"type": "string", "description": "URI to redirect to after authorization"}
  },
  "required": ["user_id", "redirect_uri"]
},
{
  "name": "mcp__calendar__handle_auth_callback",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID for token management"},
    "code": {"type": "string", "description": "Authorization code from OAuth provider"},
    "state": {"type": "string", "description": "State parameter for security verification"}
  },
  "required": ["user_id", "code", "state"]
},
{
  "name": "mcp__calendar__add_flight",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID with calendar authorization"},
    "flight_details": {"type": "object", "description": "Flight booking details", "properties": {
      "airline": {"type": "string", "description": "Airline name"},
      "flight_number": {"type": "string", "description": "Flight number"},
      "departure_airport": {"type": "string", "description": "Departure airport code"},
      "arrival_airport": {"type": "string", "description": "Arrival airport code"},
      "departure_time": {"type": "string", "description": "Departure time in ISO format"},
      "arrival_time": {"type": "string", "description": "Arrival time in ISO format"},
      "confirmation_code": {"type": "string", "description": "Booking confirmation code", "required": false},
      "seat": {"type": "string", "description": "Seat number if assigned", "required": false}
    }},
    "remind_before": {"type": "number", "description": "Hours to send reminder before flight", "default": 24}
  },
  "required": ["user_id", "flight_details"]
},
{
  "name": "mcp__calendar__add_accommodation",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID with calendar authorization"},
    "accommodation_details": {"type": "object", "description": "Accommodation booking details", "properties": {
      "name": {"type": "string", "description": "Accommodation name"},
      "address": {"type": "string", "description": "Address of the accommodation"},
      "check_in_time": {"type": "string", "description": "Check-in time in ISO format"},
      "check_out_time": {"type": "string", "description": "Check-out time in ISO format"},
      "confirmation_code": {"type": "string", "description": "Booking confirmation code", "required": false},
      "room_type": {"type": "string", "description": "Type of room booked", "required": false}
    }}
  },
  "required": ["user_id", "accommodation_details"]
},
{
  "name": "mcp__calendar__add_activity",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID with calendar authorization"},
    "activity_details": {"type": "object", "description": "Activity details", "properties": {
      "name": {"type": "string", "description": "Activity name"},
      "location": {"type": "string", "description": "Location of the activity"},
      "start_time": {"type": "string", "description": "Start time in ISO format"},
      "end_time": {"type": "string", "description": "End time in ISO format"},
      "description": {"type": "string", "description": "Activity description", "required": false},
      "booking_reference": {"type": "string", "description": "Booking reference if applicable", "required": false}
    }}
  },
  "required": ["user_id", "activity_details"]
},
{
  "name": "mcp__calendar__create_itinerary",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID with calendar authorization"},
    "trip_details": {"type": "object", "description": "Complete trip details", "properties": {
      "trip_name": {"type": "string", "description": "Name of the trip"},
      "start_date": {"type": "string", "description": "Trip start date in ISO format"},
      "end_date": {"type": "string", "description": "Trip end date in ISO format"},
      "destination": {"type": "string", "description": "Main destination of the trip"},
      "flights": {"type": "array", "description": "Array of flight details objects", "required": false},
      "accommodations": {"type": "array", "description": "Array of accommodation details objects", "required": false},
      "activities": {"type": "array", "description": "Array of activity details objects", "required": false}
    }}
  },
  "required": ["user_id", "trip_details"]
},
{
  "name": "mcp__calendar__check_availability",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID with calendar authorization"},
    "start_date": {"type": "string", "description": "Start date in ISO format"},
    "end_date": {"type": "string", "description": "End date in ISO format"},
    "timezone": {"type": "string", "description": "Timezone for the query", "default": "UTC"}
  },
  "required": ["user_id", "start_date", "end_date"]
},
{
  "name": "mcp__calendar__export_trip",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID with calendar authorization"},
    "trip_id": {"type": "string", "description": "ID of the trip to export"},
    "format": {"type": "string", "enum": ["ics", "google", "outlook", "ical"], "default": "ics", "description": "Export format"}
  },
  "required": ["user_id", "trip_id"]
},
{
  "name": "mcp__calendar__delete_event",
  "parameters": {
    "user_id": {"type": "string", "description": "User ID with calendar authorization"},
    "event_id": {"type": "string", "description": "ID of the event to delete"}
  },
  "required": ["user_id", "event_id"]
}
```

## API Integrations

### Primary: Google Calendar API

- **Key Endpoints**:

  - `/oauth2/v4/token` - OAuth token exchange
  - `/calendar/v3/calendars` - Manage calendars
  - `/calendar/v3/calendars/{calendarId}/events` - Manage events
  - `/calendar/v3/freeBusy` - Check availability

- **Authentication**:
  - OAuth 2.0 authentication flow
  - Refresh token management for long-term access
  - Client ID and Client Secret from Google Cloud Console

### Secondary: ICS Generator

- **Features**:
  - Generate iCalendar (.ics) files for cross-platform compatibility
  - Support for standard calendar properties
  - Support for attachments and alerts

## Connection Points to Existing Architecture

### Agent Integration

- **Travel Agent**:

  - Add trip components to calendar during booking process
  - Check availability during travel planning

- **Itinerary Agent**:

  - Create comprehensive calendar entries for full itineraries
  - Generate exportable calendar files for sharing

- **Time Management**:
  - Handle timezone conversions for international travel
  - Coordinate event timings across different locations

## File Structure

```plaintext
src/
  mcp/
    calendar/
      __init__.py                  # Package initialization
      server.py                    # MCP server implementation
      config.py                    # Server configuration settings
      handlers/
        __init__.py                # Module initialization
        auth_handler.py            # OAuth authentication handler
        flight_handler.py          # Flight event creation handler
        accommodation_handler.py   # Accommodation event creation handler
        activity_handler.py        # Activity event creation handler
        itinerary_handler.py       # Itinerary creation handler
        availability_handler.py    # Availability checking handler
        export_handler.py          # Calendar export handler
        delete_handler.py          # Event deletion handler
      services/
        __init__.py                # Module initialization
        google_calendar_service.py # Google Calendar API client
        ics_service.py             # ICS file generation service
        token_service.py           # OAuth token management service
      models/
        __init__.py                # Module initialization
        auth.py                    # Authentication data models
        event.py                   # Calendar event data models
        user.py                    # User data models
      transformers/
        __init__.py                # Module initialization
        event_transformer.py       # Transforms trip data to calendar events
        export_transformer.py      # Transforms events for export
      storage/
        __init__.py                # Module initialization
        supabase.py                # Supabase database integration
        memory.py                  # Knowledge graph integration
      utils/
        __init__.py                # Module initialization
        time_utils.py              # Timezone and time handling utilities
        validation.py              # Input validation utilities
        error_handling.py          # Error handling utilities
        logging.py                 # Logging configuration
```

## Key Functions and Interfaces

### Google Calendar Service

```typescript
// google_calendar_service.ts
import { google, calendar_v3 } from "googleapis";
import { OAuth2Client } from "google-auth-library";
import { TokenService } from "./token_service";
import { config } from "../config";
import {
  EventDetails,
  FlightDetails,
  AccommodationDetails,
  ActivityDetails,
} from "../models/event";
import { AuthTokens } from "../models/auth";
import {
  TimeZoneNotFoundError,
  CalendarAccessError,
} from "../utils/error_handling";

export class GoogleCalendarService {
  private tokenService: TokenService;

  constructor() {
    this.tokenService = new TokenService();
  }

  /**
   * Get OAuth2 client for a specific user
   */
  private async getOAuth2Client(userId: string): Promise<OAuth2Client> {
    try {
      // Get tokens from storage
      const tokens = await this.tokenService.getTokensForUser(userId);

      if (!tokens) {
        throw new CalendarAccessError(
          "User not authorized for calendar access"
        );
      }

      // Create and configure OAuth2 client
      const oauth2Client = new google.auth.OAuth2(
        config.GOOGLE_CLIENT_ID,
        config.GOOGLE_CLIENT_SECRET,
        config.GOOGLE_REDIRECT_URI
      );

      oauth2Client.setCredentials({
        access_token: tokens.accessToken,
        refresh_token: tokens.refreshToken,
        expiry_date: tokens.expiryDate,
      });

      // Set up token refresh callback
      oauth2Client.on("tokens", async (newTokens) => {
        if (newTokens.refresh_token) {
          // Store the new refresh token
          await this.tokenService.updateTokensForUser(userId, {
            ...tokens,
            refreshToken: newTokens.refresh_token,
            accessToken: newTokens.access_token || tokens.accessToken,
            expiryDate: newTokens.expiry_date || tokens.expiryDate,
          });
        } else if (newTokens.access_token) {
          // Update just the access token
          await this.tokenService.updateTokensForUser(userId, {
            ...tokens,
            accessToken: newTokens.access_token,
            expiryDate: newTokens.expiry_date || tokens.expiryDate,
          });
        }
      });

      return oauth2Client;
    } catch (error) {
      if (error instanceof CalendarAccessError) {
        throw error;
      }
      throw new Error(`Failed to get OAuth2 client: ${error.message}`);
    }
  }

  /**
   * Generate authorization URL for Google Calendar
   */
  public getAuthorizationUrl(userId: string, redirectUri: string): string {
    const oauth2Client = new google.auth.OAuth2(
      config.GOOGLE_CLIENT_ID,
      config.GOOGLE_CLIENT_SECRET,
      redirectUri
    );

    const state = Buffer.from(JSON.stringify({ userId })).toString("base64");

    const authUrl = oauth2Client.generateAuthUrl({
      access_type: "offline",
      scope: ["https://www.googleapis.com/auth/calendar"],
      prompt: "consent", // Force consent screen to ensure we get a refresh token
      state: state,
    });

    return authUrl;
  }

  /**
   * Handle OAuth callback and exchange code for tokens
   */
  public async handleAuthCallback(
    userId: string,
    code: string,
    state: string
  ): Promise<void> {
    try {
      // Verify state parameter matches expected user
      const decodedState = JSON.parse(Buffer.from(state, "base64").toString());
      if (decodedState.userId !== userId) {
        throw new Error("State parameter mismatch");
      }

      const oauth2Client = new google.auth.OAuth2(
        config.GOOGLE_CLIENT_ID,
        config.GOOGLE_CLIENT_SECRET,
        config.GOOGLE_REDIRECT_URI
      );

      // Exchange code for tokens
      const { tokens } = await oauth2Client.getToken(code);

      // Store tokens
      await this.tokenService.storeTokensForUser(userId, {
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        expiryDate: tokens.expiry_date,
        scope: tokens.scope,
      });
    } catch (error) {
      throw new Error(`Failed to handle auth callback: ${error.message}`);
    }
  }

  /**
   * Add a flight event to the user's calendar
   */
  public async addFlightEvent(
    userId: string,
    flightDetails: FlightDetails,
    remindBefore: number = 24
  ): Promise<string> {
    try {
      const oauth2Client = await this.getOAuth2Client(userId);
      const calendar = google.calendar({ version: "v3", auth: oauth2Client });

      // Get departure and arrival time zones
      const departureTimeZone = await this.getAirportTimeZone(
        flightDetails.departure_airport
      );
      const arrivalTimeZone = await this.getAirportTimeZone(
        flightDetails.arrival_airport
      );

      // Create event object
      const event: calendar_v3.Schema$Event = {
        summary: `Flight: ${flightDetails.airline} ${flightDetails.flight_number}`,
        location: `${flightDetails.departure_airport} to ${flightDetails.arrival_airport}`,
        description: this.generateFlightDescription(flightDetails),
        start: {
          dateTime: flightDetails.departure_time,
          timeZone: departureTimeZone,
        },
        end: {
          dateTime: flightDetails.arrival_time,
          timeZone: arrivalTimeZone,
        },
        colorId: "1", // Use airline-specific color in the future
        reminders: {
          useDefault: false,
          overrides: [
            { method: "email", minutes: remindBefore * 60 },
            { method: "popup", minutes: 120 }, // 2 hours
          ],
        },
      };

      // Add the event to the calendar
      const response = await calendar.events.insert({
        calendarId: "primary",
        requestBody: event,
      });

      // Store the event ID in our database for future reference
      await this.storeEventMapping(
        userId,
        "flight",
        flightDetails.confirmation_code,
        response.data.id
      );

      return response.data.id;
    } catch (error) {
      throw new Error(`Failed to add flight event: ${error.message}`);
    }
  }

  /**
   * Add an accommodation event to the user's calendar
   */
  public async addAccommodationEvent(
    userId: string,
    accommodationDetails: AccommodationDetails
  ): Promise<string> {
    try {
      const oauth2Client = await this.getOAuth2Client(userId);
      const calendar = google.calendar({ version: "v3", auth: oauth2Client });

      // Create event object
      const event: calendar_v3.Schema$Event = {
        summary: `Stay: ${accommodationDetails.name}`,
        location: accommodationDetails.address,
        description:
          this.generateAccommodationDescription(accommodationDetails),
        start: {
          dateTime: accommodationDetails.check_in_time,
          timeZone: "UTC", // Use actual timezone in production
        },
        end: {
          dateTime: accommodationDetails.check_out_time,
          timeZone: "UTC", // Use actual timezone in production
        },
        colorId: "2",
        reminders: {
          useDefault: false,
          overrides: [
            { method: "email", minutes: 24 * 60 }, // 1 day
            { method: "popup", minutes: 120 }, // 2 hours
          ],
        },
      };

      // Add the event to the calendar
      const response = await calendar.events.insert({
        calendarId: "primary",
        requestBody: event,
      });

      // Store the event ID in our database for future reference
      await this.storeEventMapping(
        userId,
        "accommodation",
        accommodationDetails.confirmation_code,
        response.data.id
      );

      return response.data.id;
    } catch (error) {
      throw new Error(`Failed to add accommodation event: ${error.message}`);
    }
  }

  /**
   * Add an activity event to the user's calendar
   */
  public async addActivityEvent(
    userId: string,
    activityDetails: ActivityDetails
  ): Promise<string> {
    try {
      const oauth2Client = await this.getOAuth2Client(userId);
      const calendar = google.calendar({ version: "v3", auth: oauth2Client });

      // Create event object
      const event: calendar_v3.Schema$Event = {
        summary: `Activity: ${activityDetails.name}`,
        location: activityDetails.location,
        description: activityDetails.description || "",
        start: {
          dateTime: activityDetails.start_time,
          timeZone: "UTC", // Use actual timezone in production
        },
        end: {
          dateTime: activityDetails.end_time,
          timeZone: "UTC", // Use actual timezone in production
        },
        colorId: "3",
        reminders: {
          useDefault: false,
          overrides: [
            { method: "popup", minutes: 60 }, // 1 hour
          ],
        },
      };

      // Add booking reference if available
      if (activityDetails.booking_reference) {
        event.description += `\nBooking Reference: ${activityDetails.booking_reference}`;
      }

      // Add the event to the calendar
      const response = await calendar.events.insert({
        calendarId: "primary",
        requestBody: event,
      });

      // Store the event ID in our database for future reference
      await this.storeEventMapping(
        userId,
        "activity",
        activityDetails.booking_reference,
        response.data.id
      );

      return response.data.id;
    } catch (error) {
      throw new Error(`Failed to add activity event: ${error.message}`);
    }
  }

  /**
   * Create a full trip itinerary in the user's calendar
   */
  public async createItinerary(
    userId: string,
    tripDetails: any
  ): Promise<string[]> {
    try {
      const eventIds: string[] = [];

      // Add flights to calendar
      if (tripDetails.flights && tripDetails.flights.length > 0) {
        for (const flight of tripDetails.flights) {
          const eventId = await this.addFlightEvent(userId, flight);
          eventIds.push(eventId);
        }
      }

      // Add accommodations to calendar
      if (tripDetails.accommodations && tripDetails.accommodations.length > 0) {
        for (const accommodation of tripDetails.accommodations) {
          const eventId = await this.addAccommodationEvent(
            userId,
            accommodation
          );
          eventIds.push(eventId);
        }
      }

      // Add activities to calendar
      if (tripDetails.activities && tripDetails.activities.length > 0) {
        for (const activity of tripDetails.activities) {
          const eventId = await this.addActivityEvent(userId, activity);
          eventIds.push(eventId);
        }
      }

      // Store trip mapping
      await this.storeTripMapping(userId, tripDetails.trip_name, eventIds);

      return eventIds;
    } catch (error) {
      throw new Error(`Failed to create itinerary: ${error.message}`);
    }
  }

  /**
   * Check user's calendar availability
   */
  public async checkAvailability(
    userId: string,
    startDate: string,
    endDate: string,
    timezone: string = "UTC"
  ): Promise<any> {
    try {
      const oauth2Client = await this.getOAuth2Client(userId);
      const calendar = google.calendar({ version: "v3", auth: oauth2Client });

      // Query for busy times
      const response = await calendar.freebusy.query({
        requestBody: {
          timeMin: startDate,
          timeMax: endDate,
          timeZone: timezone,
          items: [{ id: "primary" }],
        },
      });

      // Process and format busy periods
      const busyPeriods = response.data.calendars.primary.busy || [];

      // Format into more user-friendly structure
      const availability = {
        timeRange: {
          start: startDate,
          end: endDate,
          timezone: timezone,
        },
        busyPeriods: busyPeriods.map((period) => ({
          start: period.start,
          end: period.end,
        })),
        isBusy: busyPeriods.length > 0,
      };

      return availability;
    } catch (error) {
      throw new Error(`Failed to check availability: ${error.message}`);
    }
  }

  /**
   * Delete an event from the user's calendar
   */
  public async deleteEvent(userId: string, eventId: string): Promise<boolean> {
    try {
      const oauth2Client = await this.getOAuth2Client(userId);
      const calendar = google.calendar({ version: "v3", auth: oauth2Client });

      // Delete the event
      await calendar.events.delete({
        calendarId: "primary",
        eventId: eventId,
      });

      // Remove the event mapping from our database
      await this.removeEventMapping(userId, eventId);

      return true;
    } catch (error) {
      throw new Error(`Failed to delete event: ${error.message}`);
    }
  }

  /**
   * Export a trip as a calendar file or URL
   */
  public async exportTrip(
    userId: string,
    tripId: string,
    format: string
  ): Promise<string> {
    try {
      // Get all event IDs associated with the trip
      const eventIds = await this.getTripEvents(userId, tripId);

      if (format === "google") {
        // Generate Google Calendar link
        return this.generateGoogleCalendarUrl(userId, eventIds);
      } else {
        // For ics, outlook, ical formats
        return await this.generateICSFile(userId, eventIds);
      }
    } catch (error) {
      throw new Error(`Failed to export trip: ${error.message}`);
    }
  }

  // Helper methods

  /**
   * Get timezone for an airport code
   */
  private async getAirportTimeZone(airportCode: string): Promise<string> {
    // In a real implementation, this would query a database of airport timezones
    // For now, return UTC
    return "UTC";
  }

  /**
   * Generate description for flight events
   */
  private generateFlightDescription(flight: FlightDetails): string {
    let description = `
Airline: ${flight.airline}
Flight: ${flight.flight_number}

DEPARTURE
Airport: ${flight.departure_airport}
Time: ${new Date(flight.departure_time).toLocaleString()}

ARRIVAL
Airport: ${flight.arrival_airport}
Time: ${new Date(flight.arrival_time).toLocaleString()}
`;

    if (flight.confirmation_code) {
      description += `\nConfirmation Code: ${flight.confirmation_code}`;
    }

    if (flight.seat) {
      description += `\nSeat: ${flight.seat}`;
    }

    return description;
  }

  /**
   * Generate description for accommodation events
   */
  private generateAccommodationDescription(
    accommodation: AccommodationDetails
  ): string {
    let description = `
Accommodation: ${accommodation.name}
Address: ${accommodation.address}

Check-in: ${new Date(accommodation.check_in_time).toLocaleString()}
Check-out: ${new Date(accommodation.check_out_time).toLocaleString()}
`;

    if (accommodation.confirmation_code) {
      description += `\nConfirmation Code: ${accommodation.confirmation_code}`;
    }

    if (accommodation.room_type) {
      description += `\nRoom Type: ${accommodation.room_type}`;
    }

    return description;
  }

  /**
   * Store mapping between external booking ID and calendar event ID
   */
  private async storeEventMapping(
    userId: string,
    type: string,
    bookingId: string,
    eventId: string
  ): Promise<void> {
    // Implementation would store this mapping in the database
    // This is a stub implementation
  }

  /**
   * Remove event mapping
   */
  private async removeEventMapping(
    userId: string,
    eventId: string
  ): Promise<void> {
    // Implementation would remove this mapping from the database
    // This is a stub implementation
  }

  /**
   * Store mapping between trip and its events
   */
  private async storeTripMapping(
    userId: string,
    tripName: string,
    eventIds: string[]
  ): Promise<void> {
    // Implementation would store this mapping in the database
    // This is a stub implementation
  }

  /**
   * Get all event IDs associated with a trip
   */
  private async getTripEvents(
    userId: string,
    tripId: string
  ): Promise<string[]> {
    // Implementation would query the database for all events associated with this trip
    // This is a stub implementation
    return [];
  }

  /**
   * Generate Google Calendar URL for events
   */
  private generateGoogleCalendarUrl(
    userId: string,
    eventIds: string[]
  ): string {
    // Implementation would generate a URL that opens these events in Google Calendar
    // This is a stub implementation
    return "https://calendar.google.com/calendar";
  }

  /**
   * Generate ICS file for events
   */
  private async generateICSFile(
    userId: string,
    eventIds: string[]
  ): Promise<string> {
    // Implementation would generate an ICS file containing these events
    // This is a stub implementation
    return "data:text/calendar;charset=utf-8,BEGIN:VCALENDAR...";
  }
}
```

### Token Service

```typescript
// token_service.ts
import { supabase } from "../storage/supabase";
import { AuthTokens } from "../models/auth";
import { EncryptionService } from "./encryption_service";
import { config } from "../config";

export class TokenService {
  private encryptionService: EncryptionService;

  constructor() {
    this.encryptionService = new EncryptionService(config.ENCRYPTION_KEY);
  }

  /**
   * Store OAuth tokens for a user
   */
  public async storeTokensForUser(
    userId: string,
    tokens: AuthTokens
  ): Promise<void> {
    try {
      // Encrypt sensitive token data
      const encryptedAccessToken = this.encryptionService.encrypt(
        tokens.accessToken
      );
      const encryptedRefreshToken = this.encryptionService.encrypt(
        tokens.refreshToken
      );

      // Check if user already has tokens
      const { data: existingTokens } = await supabase
        .from("auth_tokens")
        .select("*")
        .eq("user_id", userId)
        .eq("provider", "google_calendar")
        .single();

      if (existingTokens) {
        // Update existing tokens
        await supabase
          .from("auth_tokens")
          .update({
            access_token: encryptedAccessToken,
            refresh_token: encryptedRefreshToken,
            expiry_date: tokens.expiryDate,
            scope: tokens.scope,
            updated_at: new Date().toISOString(),
          })
          .eq("id", existingTokens.id);
      } else {
        // Insert new tokens
        await supabase.from("auth_tokens").insert({
          user_id: userId,
          provider: "google_calendar",
          access_token: encryptedAccessToken,
          refresh_token: encryptedRefreshToken,
          expiry_date: tokens.expiryDate,
          scope: tokens.scope,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }
    } catch (error) {
      throw new Error(`Failed to store tokens: ${error.message}`);
    }
  }

  /**
   * Get OAuth tokens for a user
   */
  public async getTokensForUser(userId: string): Promise<AuthTokens | null> {
    try {
      // Query for tokens
      const { data: tokenData, error } = await supabase
        .from("auth_tokens")
        .select("*")
        .eq("user_id", userId)
        .eq("provider", "google_calendar")
        .single();

      if (error || !tokenData) {
        return null;
      }

      // Decrypt tokens
      const accessToken = this.encryptionService.decrypt(
        tokenData.access_token
      );
      const refreshToken = this.encryptionService.decrypt(
        tokenData.refresh_token
      );

      return {
        accessToken,
        refreshToken,
        expiryDate: tokenData.expiry_date,
        scope: tokenData.scope,
      };
    } catch (error) {
      throw new Error(`Failed to get tokens: ${error.message}`);
    }
  }

  /**
   * Update OAuth tokens for a user
   */
  public async updateTokensForUser(
    userId: string,
    tokens: AuthTokens
  ): Promise<void> {
    try {
      // Encrypt sensitive token data
      const encryptedAccessToken = this.encryptionService.encrypt(
        tokens.accessToken
      );
      const encryptedRefreshToken = this.encryptionService.encrypt(
        tokens.refreshToken
      );

      // Update tokens
      await supabase
        .from("auth_tokens")
        .update({
          access_token: encryptedAccessToken,
          refresh_token: encryptedRefreshToken,
          expiry_date: tokens.expiryDate,
          scope: tokens.scope,
          updated_at: new Date().toISOString(),
        })
        .eq("user_id", userId)
        .eq("provider", "google_calendar");
    } catch (error) {
      throw new Error(`Failed to update tokens: ${error.message}`);
    }
  }

  /**
   * Delete OAuth tokens for a user
   */
  public async deleteTokensForUser(userId: string): Promise<void> {
    try {
      await supabase
        .from("auth_tokens")
        .delete()
        .eq("user_id", userId)
        .eq("provider", "google_calendar");
    } catch (error) {
      throw new Error(`Failed to delete tokens: ${error.message}`);
    }
  }
}
```

### ICS Service

```typescript
// ics_service.ts
import * as ics from "ics";
import {
  EventDetails,
  FlightDetails,
  AccommodationDetails,
  ActivityDetails,
} from "../models/event";

export class ICSService {
  /**
   * Generate ICS file content for a single event
   */
  public generateEventICS(eventDetails: EventDetails): Promise<string> {
    return new Promise((resolve, reject) => {
      let icsEvent: any;

      if (eventDetails.type === "flight") {
        icsEvent = this.createFlightEvent(eventDetails as FlightDetails);
      } else if (eventDetails.type === "accommodation") {
        icsEvent = this.createAccommodationEvent(
          eventDetails as AccommodationDetails
        );
      } else if (eventDetails.type === "activity") {
        icsEvent = this.createActivityEvent(eventDetails as ActivityDetails);
      } else {
        reject(new Error("Unsupported event type"));
        return;
      }

      ics.createEvent(icsEvent, (error, value) => {
        if (error) {
          reject(error);
        } else {
          resolve(value);
        }
      });
    });
  }

  /**
   * Generate ICS file content for multiple events
   */
  public generateMultipleEventsICS(events: EventDetails[]): Promise<string> {
    return new Promise((resolve, reject) => {
      const icsEvents = events
        .map((event) => {
          if (event.type === "flight") {
            return this.createFlightEvent(event as FlightDetails);
          } else if (event.type === "accommodation") {
            return this.createAccommodationEvent(event as AccommodationDetails);
          } else if (event.type === "activity") {
            return this.createActivityEvent(event as ActivityDetails);
          }
          return null;
        })
        .filter((event) => event !== null);

      if (icsEvents.length === 0) {
        reject(new Error("No valid events to convert"));
        return;
      }

      ics.createEvents(icsEvents, (error, value) => {
        if (error) {
          reject(error);
        } else {
          resolve(value);
        }
      });
    });
  }

  /**
   * Create ICS event for a flight
   */
  private createFlightEvent(flight: FlightDetails): any {
    const startDate = new Date(flight.departure_time);
    const endDate = new Date(flight.arrival_time);

    return {
      start: [
        startDate.getUTCFullYear(),
        startDate.getUTCMonth() + 1,
        startDate.getUTCDate(),
        startDate.getUTCHours(),
        startDate.getUTCMinutes(),
      ],
      end: [
        endDate.getUTCFullYear(),
        endDate.getUTCMonth() + 1,
        endDate.getUTCDate(),
        endDate.getUTCHours(),
        endDate.getUTCMinutes(),
      ],
      title: `Flight: ${flight.airline} ${flight.flight_number}`,
      description: this.generateFlightDescription(flight),
      location: `${flight.departure_airport} to ${flight.arrival_airport}`,
      status: "CONFIRMED",
      busyStatus: "BUSY",
      organizer: { name: "TripSage", email: "calendar@tripsage.com" },
      alarms: [{ action: "display", trigger: { hours: 24, before: true } }],
    };
  }

  /**
   * Create ICS event for an accommodation
   */
  private createAccommodationEvent(accommodation: AccommodationDetails): any {
    const startDate = new Date(accommodation.check_in_time);
    const endDate = new Date(accommodation.check_out_time);

    return {
      start: [
        startDate.getUTCFullYear(),
        startDate.getUTCMonth() + 1,
        startDate.getUTCDate(),
        startDate.getUTCHours(),
        startDate.getUTCMinutes(),
      ],
      end: [
        endDate.getUTCFullYear(),
        endDate.getUTCMonth() + 1,
        endDate.getUTCDate(),
        endDate.getUTCHours(),
        endDate.getUTCMinutes(),
      ],
      title: `Stay: ${accommodation.name}`,
      description: this.generateAccommodationDescription(accommodation),
      location: accommodation.address,
      status: "CONFIRMED",
      busyStatus: "FREE",
      organizer: { name: "TripSage", email: "calendar@tripsage.com" },
      alarms: [{ action: "display", trigger: { hours: 24, before: true } }],
    };
  }

  /**
   * Create ICS event for an activity
   */
  private createActivityEvent(activity: ActivityDetails): any {
    const startDate = new Date(activity.start_time);
    const endDate = new Date(activity.end_time);

    let description = activity.description || "";
    if (activity.booking_reference) {
      description += `\nBooking Reference: ${activity.booking_reference}`;
    }

    return {
      start: [
        startDate.getUTCFullYear(),
        startDate.getUTCMonth() + 1,
        startDate.getUTCDate(),
        startDate.getUTCHours(),
        startDate.getUTCMinutes(),
      ],
      end: [
        endDate.getUTCFullYear(),
        endDate.getUTCMonth() + 1,
        endDate.getUTCDate(),
        endDate.getUTCHours(),
        endDate.getUTCMinutes(),
      ],
      title: `Activity: ${activity.name}`,
      description: description,
      location: activity.location,
      status: "CONFIRMED",
      busyStatus: "BUSY",
      organizer: { name: "TripSage", email: "calendar@tripsage.com" },
      alarms: [{ action: "display", trigger: { hours: 1, before: true } }],
    };
  }

  /**
   * Generate description for flight events
   */
  private generateFlightDescription(flight: FlightDetails): string {
    let description = `
Airline: ${flight.airline}
Flight: ${flight.flight_number}

DEPARTURE
Airport: ${flight.departure_airport}
Time: ${new Date(flight.departure_time).toUTCString()}

ARRIVAL
Airport: ${flight.arrival_airport}
Time: ${new Date(flight.arrival_time).toUTCString()}
`;

    if (flight.confirmation_code) {
      description += `\nConfirmation Code: ${flight.confirmation_code}`;
    }

    if (flight.seat) {
      description += `\nSeat: ${flight.seat}`;
    }

    return description;
  }

  /**
   * Generate description for accommodation events
   */
  private generateAccommodationDescription(
    accommodation: AccommodationDetails
  ): string {
    let description = `
Accommodation: ${accommodation.name}
Address: ${accommodation.address}

Check-in: ${new Date(accommodation.check_in_time).toUTCString()}
Check-out: ${new Date(accommodation.check_out_time).toUTCString()}
`;

    if (accommodation.confirmation_code) {
      description += `\nConfirmation Code: ${accommodation.confirmation_code}`;
    }

    if (accommodation.room_type) {
      description += `\nRoom Type: ${accommodation.room_type}`;
    }

    return description;
  }
}
```

### Main Server Implementation

```typescript
// server.ts
import express from "express";
import bodyParser from "body-parser";
import { AuthHandler } from "./handlers/auth_handler";
import { FlightHandler } from "./handlers/flight_handler";
import { AccommodationHandler } from "./handlers/accommodation_handler";
import { ActivityHandler } from "./handlers/activity_handler";
import { ItineraryHandler } from "./handlers/itinerary_handler";
import { AvailabilityHandler } from "./handlers/availability_handler";
import { ExportHandler } from "./handlers/export_handler";
import { DeleteHandler } from "./handlers/delete_handler";
import { logRequest, logError, logInfo } from "./utils/logging";
import { config } from "./config";

const app = express();
app.use(bodyParser.json());

// Initialize handlers
const authHandler = new AuthHandler();
const flightHandler = new FlightHandler();
const accommodationHandler = new AccommodationHandler();
const activityHandler = new ActivityHandler();
const itineraryHandler = new ItineraryHandler();
const availabilityHandler = new AvailabilityHandler();
const exportHandler = new ExportHandler();
const deleteHandler = new DeleteHandler();

// Handle MCP tool requests
app.post("/api/mcp/calendar/authorize", async (req, res) => {
  try {
    logRequest("authorize", req.body);
    const result = await authHandler.handleAuthorize(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in authorize: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/handle_auth_callback", async (req, res) => {
  try {
    logRequest("handle_auth_callback", req.body);
    const result = await authHandler.handleAuthCallback(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in handle_auth_callback: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/add_flight", async (req, res) => {
  try {
    logRequest("add_flight", req.body);
    const result = await flightHandler.handleAddFlight(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in add_flight: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/add_accommodation", async (req, res) => {
  try {
    logRequest("add_accommodation", req.body);
    const result = await accommodationHandler.handleAddAccommodation(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in add_accommodation: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/add_activity", async (req, res) => {
  try {
    logRequest("add_activity", req.body);
    const result = await activityHandler.handleAddActivity(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in add_activity: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/create_itinerary", async (req, res) => {
  try {
    logRequest("create_itinerary", req.body);
    const result = await itineraryHandler.handleCreateItinerary(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in create_itinerary: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/check_availability", async (req, res) => {
  try {
    logRequest("check_availability", req.body);
    const result = await availabilityHandler.handleCheckAvailability(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in check_availability: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/export_trip", async (req, res) => {
  try {
    logRequest("export_trip", req.body);
    const result = await exportHandler.handleExportTrip(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in export_trip: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/calendar/delete_event", async (req, res) => {
  try {
    logRequest("delete_event", req.body);
    const result = await deleteHandler.handleDeleteEvent(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in delete_event: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

// Start server
const PORT = process.env.PORT || 3004;
app.listen(PORT, () => {
  logInfo(`Calendar MCP Server running on port ${PORT}`);
});
```

## Data Formats

### Input Format Examples

```json
// authorize input
{
  "user_id": "user123",
  "redirect_uri": "https://app.tripsage.com/auth/callback"
}

// handle_auth_callback input
{
  "user_id": "user123",
  "code": "4/P7q7W91a-oMsCeLvIaQm6bTrgtp7",
  "state": "eyJ1c2VySWQiOiJ1c2VyMTIzIn0="
}

// add_flight input
{
  "user_id": "user123",
  "flight_details": {
    "airline": "United Airlines",
    "flight_number": "UA123",
    "departure_airport": "LAX",
    "arrival_airport": "JFK",
    "departure_time": "2025-06-15T08:00:00Z",
    "arrival_time": "2025-06-15T16:30:00Z",
    "confirmation_code": "ABC123",
    "seat": "24A"
  },
  "remind_before": 48
}

// create_itinerary input
{
  "user_id": "user123",
  "trip_details": {
    "trip_name": "Summer Vacation 2025",
    "start_date": "2025-06-15T00:00:00Z",
    "end_date": "2025-06-22T23:59:59Z",
    "destination": "New York City",
    "flights": [
      {
        "airline": "United Airlines",
        "flight_number": "UA123",
        "departure_airport": "LAX",
        "arrival_airport": "JFK",
        "departure_time": "2025-06-15T08:00:00Z",
        "arrival_time": "2025-06-15T16:30:00Z",
        "confirmation_code": "ABC123",
        "seat": "24A"
      },
      {
        "airline": "United Airlines",
        "flight_number": "UA456",
        "departure_airport": "JFK",
        "arrival_airport": "LAX",
        "departure_time": "2025-06-22T10:00:00Z",
        "arrival_time": "2025-06-22T13:30:00Z",
        "confirmation_code": "DEF456",
        "seat": "18F"
      }
    ],
    "accommodations": [
      {
        "name": "The Standard Hotel",
        "address": "25 Cooper Square, New York, NY 10003",
        "check_in_time": "2025-06-15T15:00:00Z",
        "check_out_time": "2025-06-22T11:00:00Z",
        "confirmation_code": "HT789012",
        "room_type": "Deluxe King"
      }
    ],
    "activities": [
      {
        "name": "Broadway Show - Hamilton",
        "location": "Richard Rodgers Theatre, 226 W 46th St, New York, NY 10036",
        "start_time": "2025-06-18T19:00:00Z",
        "end_time": "2025-06-18T22:00:00Z",
        "description": "Award-winning musical about Alexander Hamilton",
        "booking_reference": "TKT345678"
      },
      {
        "name": "Statue of Liberty Tour",
        "location": "Battery Park, New York, NY",
        "start_time": "2025-06-16T09:00:00Z",
        "end_time": "2025-06-16T13:00:00Z",
        "description": "Guided tour of the Statue of Liberty and Ellis Island",
        "booking_reference": "TUR901234"
      }
    ]
  }
}
```

### Output Format Examples

```json
// authorize output
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=123456789012-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fapp.tripsage.com%2Fauth%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar&response_type=code&access_type=offline&prompt=consent&state=eyJ1c2VySWQiOiJ1c2VyMTIzIn0%3D",
  "message": "Please visit this URL to authorize TripSage to access your Google Calendar."
}

// handle_auth_callback output
{
  "success": true,
  "message": "Successfully authenticated with Google Calendar.",
  "user_id": "user123"
}

// add_flight output
{
  "success": true,
  "event_id": "1234567890abcdef",
  "event_details": {
    "summary": "Flight: United Airlines UA123",
    "start": "2025-06-15T08:00:00Z",
    "end": "2025-06-15T16:30:00Z",
    "calendar_link": "https://calendar.google.com/calendar/event?eid=MTIzNDU2Nzg5MGFiY2RlZg"
  },
  "message": "Flight added to calendar successfully."
}

// create_itinerary output
{
  "success": true,
  "event_count": 5,
  "event_ids": [
    "1234567890abcdef",
    "2345678901bcdef",
    "3456789012cdef",
    "4567890123def",
    "5678901234ef"
  ],
  "trip_details": {
    "trip_name": "Summer Vacation 2025",
    "destination": "New York City",
    "date_range": "Jun 15-22, 2025"
  },
  "message": "Trip itinerary created successfully in calendar."
}

// check_availability output
{
  "time_range": {
    "start": "2025-06-15T00:00:00Z",
    "end": "2025-06-22T23:59:59Z",
    "timezone": "America/New_York"
  },
  "busy_periods": [
    {
      "start": "2025-06-16T14:00:00Z",
      "end": "2025-06-16T16:00:00Z"
    },
    {
      "start": "2025-06-18T19:00:00Z",
      "end": "2025-06-18T21:00:00Z"
    }
  ],
  "is_busy": true,
  "percentage_available": 97.5,
  "message": "User has 2 events during the requested period."
}

// export_trip output
{
  "success": true,
  "format": "ics",
  "download_url": "data:text/calendar;charset=utf-8,BEGIN:VCALENDAR%0AVERSION:2.0%0APRODID:-//TripSage//Calendar//EN%0A...",
  "message": "Trip calendar exported successfully."
}
```

## Implementation Considerations

### OAuth Flow Implementation

1. **Authorization Process**:

   - User requests calendar integration
   - TripSage redirects to Google OAuth consent screen
   - User grants permission
   - Google redirects back with authorization code
   - TripSage exchanges code for access and refresh tokens
   - TripSage stores tokens securely for future use

2. **Token Security**:

   - Encrypt tokens before storing in database
   - Use refresh tokens for long-term access
   - Implement token rotation for security
   - Set proper OAuth 2.0 scopes to limit access

3. **Consent Screen Configuration**:
   - Set up proper branding and information
   - Request only necessary scopes
   - Explain clearly what access is needed and why

### Error Handling

- **Authentication Failures**: Clear error messages for auth issues
- **Token Expiration**: Automatic refresh of expired tokens
- **API Limits**: Handle Google Calendar API quotas and rate limits
- **Event Creation Failures**: Detailed error reporting and retry mechanisms

### Performance Optimization

- **Batch Operations**: Group calendar operations when possible
- **Caching**: Cache calendar availability and frequently accessed data
- **Partial Updates**: Only update changed event properties

### Security

- **Data Encryption**: Encrypt all stored tokens and sensitive data
- **Minimal Scope**: Request only the permissions needed
- **Token Validation**: Verify all tokens and state parameters
- **Secure Communication**: Use HTTPS for all API calls

## Integration with Agent Architecture

The Calendar MCP Server will be exposed to the TripSage agents through a client library that handles the MCP communication protocol. This integration will be implemented in the `src/agents/mcp_integration.py` file:

```python
# src/agents/mcp_integration.py

class CalendarMCPClient:
    """Client for interacting with the Calendar MCP Server"""

    def __init__(self, server_url):
        self.server_url = server_url

    async def authorize(self, user_id, redirect_uri):
        """Get authorization URL for Google Calendar access"""
        try:
            # Implement MCP call to calendar server
            result = await call_mcp_tool(
                "mcp__calendar__authorize",
                {
                    "user_id": user_id,
                    "redirect_uri": redirect_uri
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error authorizing calendar: {str(e)}")
            raise

    async def handle_auth_callback(self, user_id, code, state):
        """Handle OAuth callback and complete authentication"""
        try:
            # Implement MCP call to calendar server
            result = await call_mcp_tool(
                "mcp__calendar__handle_auth_callback",
                {
                    "user_id": user_id,
                    "code": code,
                    "state": state
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error handling auth callback: {str(e)}")
            raise

    async def add_flight(self, user_id, flight_details, remind_before=24):
        """Add a flight to the user's calendar"""
        try:
            # Implement MCP call to calendar server
            result = await call_mcp_tool(
                "mcp__calendar__add_flight",
                {
                    "user_id": user_id,
                    "flight_details": flight_details,
                    "remind_before": remind_before
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error adding flight to calendar: {str(e)}")
            raise

    # Additional methods for other MCP tools...
```

## Deployment Strategy

The Calendar MCP Server will be containerized using Docker and deployed as a standalone service. This allows for independent scaling and updates:

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

ENV NODE_ENV=production
ENV PORT=3004

EXPOSE 3004

CMD ["node", "dist/server.js"]
```

### Resource Requirements

- **CPU**: Low to moderate (0.5-1 vCPU recommended)
- **Memory**: 512MB minimum, 1GB recommended
- **Storage**: Minimal (primarily for code and logs)
- **Network**: Low to moderate (API calls to Google)

### Monitoring

- **Health Endpoint**: `/health` endpoint for monitoring
- **Metrics**: Request count, authentication success rate, event creation success rate
- **Logging**: Structured logs with request/response details
- **Alerts**: Set up for authentication failures or high error rates
