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

```
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

3. Save the file and restart your TripSage application

## Implementation Guide

### 1. Calendar Service Implementation

Create a file `src/services/calendar/google-calendar-service.js`:

```javascript
const { google } = require("googleapis");
const { OAuth2Client } = require("google-auth-library");
const { v4: uuidv4 } = require("uuid");
const db = require("../../utils/db");

class GoogleCalendarService {
  /**
   * Initializes the service with OAuth credentials
   */
  constructor() {
    this.clientId = process.env.GOOGLE_CLIENT_ID;
    this.clientSecret = process.env.GOOGLE_CLIENT_SECRET;
    this.redirectUri = process.env.GOOGLE_REDIRECT_URI;
  }

  /**
   * Creates an OAuth client for a given user
   * @private
   * @param {Object} tokens User's OAuth tokens
   * @returns {OAuth2Client} Authenticated OAuth client
   */
  _createOAuthClient(tokens = null) {
    const oAuth2Client = new OAuth2Client(
      this.clientId,
      this.clientSecret,
      this.redirectUri
    );

    if (tokens) {
      oAuth2Client.setCredentials(tokens);
    }

    return oAuth2Client;
  }

  /**
   * Gets authentication URL for user to authorize calendar access
   * @param {string} userId User identifier
   * @returns {string} Authorization URL
   */
  getAuthUrl(userId) {
    const oAuth2Client = this._createOAuthClient();

    // Generate a state parameter to prevent CSRF
    const state = uuidv4();

    // Store state parameter for verification
    db.collection("oauth_states").insertOne({
      state,
      userId,
      created: new Date(),
    });

    const authUrl = oAuth2Client.generateAuthUrl({
      access_type: "offline",
      scope: [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
      ],
      state: state,
      // Force consent to ensure we get a refresh token
      prompt: "consent",
    });

    return authUrl;
  }

  /**
   * Handle OAuth callback and retrieve tokens
   * @param {string} code Authorization code from callback
   * @param {string} state State parameter from callback
   * @returns {Promise<Object>} OAuth tokens
   */
  async handleCallback(code, state) {
    // Verify state parameter
    const stateRecord = await db.collection("oauth_states").findOne({ state });
    if (!stateRecord) {
      throw new Error("Invalid state parameter");
    }

    // Exchange code for tokens
    const oAuth2Client = this._createOAuthClient();
    const { tokens } = await oAuth2Client.getToken(code);

    // Store tokens for the user
    await db.collection("user_tokens").updateOne(
      { userId: stateRecord.userId },
      {
        $set: {
          google_calendar_tokens: tokens,
          updated: new Date(),
        },
      },
      { upsert: true }
    );

    // Clean up state record
    await db.collection("oauth_states").deleteOne({ state });

    return {
      userId: stateRecord.userId,
      tokens,
    };
  }

  /**
   * Get user tokens from database
   * @param {string} userId User identifier
   * @returns {Promise<Object>} User tokens
   */
  async getUserTokens(userId) {
    const userRecord = await db.collection("user_tokens").findOne({ userId });
    if (!userRecord || !userRecord.google_calendar_tokens) {
      return null;
    }

    return userRecord.google_calendar_tokens;
  }

  /**
   * Create an authenticated calendar client for a user
   * @param {string} userId User identifier
   * @returns {Promise<Object>} Calendar client
   */
  async getCalendarClient(userId) {
    const tokens = await this.getUserTokens(userId);

    if (!tokens) {
      throw new Error("User not authenticated with Google Calendar");
    }

    const oAuth2Client = this._createOAuthClient(tokens);

    // Check if token is expired and needs refresh
    if (tokens.expiry_date < Date.now()) {
      try {
        const { credentials } = await oAuth2Client.refreshAccessToken();

        // Update tokens in database
        await db.collection("user_tokens").updateOne(
          { userId },
          {
            $set: {
              google_calendar_tokens: credentials,
              updated: new Date(),
            },
          }
        );

        // Update client with new credentials
        oAuth2Client.setCredentials(credentials);
      } catch (error) {
        console.error("Error refreshing access token:", error);
        throw new Error(
          "Failed to refresh access token, please re-authenticate"
        );
      }
    }

    return google.calendar({ version: "v3", auth: oAuth2Client });
  }

  /**
   * Add flight to user's calendar
   * @param {string} userId User identifier
   * @param {Object} flightDetails Flight booking details
   * @returns {Promise<Object>} Created calendar event
   */
  async addFlightToCalendar(userId, flightDetails) {
    const calendar = await this.getCalendarClient(userId);

    // Format event details
    const event = {
      summary: `Flight: ${flightDetails.airline} ${flightDetails.flightNumber}`,
      location: `${flightDetails.departureAirport} to ${flightDetails.arrivalAirport}`,
      description: `
Confirmation: ${flightDetails.confirmationCode}
Airline: ${flightDetails.airline}
Flight: ${flightDetails.flightNumber}

DEPARTURE
Airport: ${flightDetails.departureAirport}
Terminal: ${flightDetails.departureTerminal || "N/A"}
Time: ${new Date(flightDetails.departureTime).toLocaleString()}

ARRIVAL
Airport: ${flightDetails.arrivalAirport}
Terminal: ${flightDetails.arrivalTerminal || "N/A"}
Time: ${new Date(flightDetails.arrivalTime).toLocaleString()}

Seat: ${flightDetails.seat || "Not assigned"}
Booking Status: ${flightDetails.status || "Confirmed"}
`,
      start: {
        dateTime: flightDetails.departureTime,
        timeZone: flightDetails.departureTimezone || "UTC",
      },
      end: {
        dateTime: flightDetails.arrivalTime,
        timeZone: flightDetails.arrivalTimezone || "UTC",
      },
      // Blue color for flights
      colorId: "1",
      // Smart reminders
      reminders: {
        useDefault: false,
        overrides: [
          // Check-in reminder (if applicable)
          ...(flightDetails.checkInTime
            ? [
                {
                  method: "email",
                  minutes: Math.floor(
                    (new Date(flightDetails.departureTime) -
                      new Date(flightDetails.checkInTime)) /
                      60000
                  ),
                },
              ]
            : []),
          // General flight reminders
          { method: "email", minutes: 24 * 60 }, // 24 hours before
          { method: "popup", minutes: 3 * 60 }, // 3 hours before
        ],
      },
    };

    try {
      const response = await calendar.events.insert({
        calendarId: "primary",
        resource: event,
      });

      // Store mapping between flight booking and calendar event
      await db.collection("calendar_events").insertOne({
        userId,
        eventType: "flight",
        bookingId: flightDetails.bookingId || flightDetails.confirmationCode,
        eventId: response.data.id,
        created: new Date(),
      });

      return response.data;
    } catch (error) {
      console.error("Error adding flight to calendar:", error);
      throw new Error(`Failed to add flight to calendar: ${error.message}`);
    }
  }

  /**
   * Add accommodation to user's calendar
   * @param {string} userId User identifier
   * @param {Object} accommodationDetails Accommodation booking details
   * @returns {Promise<Object>} Created calendar event
   */
  async addAccommodationToCalendar(userId, accommodationDetails) {
    const calendar = await this.getCalendarClient(userId);

    // Create an all-day event spanning the entire stay
    const event = {
      summary: `Stay: ${accommodationDetails.propertyName}`,
      location: accommodationDetails.address,
      description: `
Confirmation: ${accommodationDetails.confirmationCode}
Property: ${accommodationDetails.propertyName}
Address: ${accommodationDetails.address}

CHECK-IN
Date: ${new Date(accommodationDetails.checkInDate).toLocaleDateString()}
Time: ${accommodationDetails.checkInTime || "Standard check-in time"}

CHECK-OUT
Date: ${new Date(accommodationDetails.checkOutDate).toLocaleDateString()}
Time: ${accommodationDetails.checkOutTime || "Standard check-out time"}

Guests: ${accommodationDetails.guests || 1}
Room/Unit: ${accommodationDetails.roomType || "Standard room"}
Booking Status: ${accommodationDetails.status || "Confirmed"}
`,
      // All-day event with check-in date
      start: {
        date: accommodationDetails.checkInDate.split("T")[0],
      },
      // End date is exclusive in Google Calendar, so we use the check-out date
      end: {
        date: accommodationDetails.checkOutDate.split("T")[0],
      },
      // Green color for accommodations
      colorId: "2",
      reminders: {
        useDefault: false,
        overrides: [
          { method: "email", minutes: 24 * 60 }, // 24 hours before check-in
          { method: "popup", minutes: 24 * 60 }, // 24 hours before check-in
        ],
      },
    };

    try {
      const response = await calendar.events.insert({
        calendarId: "primary",
        resource: event,
      });

      // Store mapping between accommodation booking and calendar event
      await db.collection("calendar_events").insertOne({
        userId,
        eventType: "accommodation",
        bookingId:
          accommodationDetails.bookingId ||
          accommodationDetails.confirmationCode,
        eventId: response.data.id,
        created: new Date(),
      });

      return response.data;
    } catch (error) {
      console.error("Error adding accommodation to calendar:", error);
      throw new Error(
        `Failed to add accommodation to calendar: ${error.message}`
      );
    }
  }

  /**
   * Add activity to user's calendar
   * @param {string} userId User identifier
   * @param {Object} activityDetails Activity details
   * @returns {Promise<Object>} Created calendar event
   */
  async addActivityToCalendar(userId, activityDetails) {
    const calendar = await this.getCalendarClient(userId);

    const event = {
      summary: `Activity: ${activityDetails.name}`,
      location: activityDetails.location,
      description: `
Activity: ${activityDetails.name}
${
  activityDetails.confirmationCode
    ? `Confirmation: ${activityDetails.confirmationCode}`
    : ""
}
Location: ${activityDetails.location}
${
  activityDetails.description
    ? `Description: ${activityDetails.description}`
    : ""
}

Date: ${new Date(activityDetails.startTime).toLocaleDateString()}
Time: ${new Date(activityDetails.startTime).toLocaleTimeString()} - ${new Date(
        activityDetails.endTime
      ).toLocaleTimeString()}

Participants: ${activityDetails.participants || 1}
${
  activityDetails.additionalInfo
    ? `Additional Information: ${activityDetails.additionalInfo}`
    : ""
}
`,
      start: {
        dateTime: activityDetails.startTime,
        timeZone: activityDetails.timezone || "UTC",
      },
      end: {
        dateTime: activityDetails.endTime,
        timeZone: activityDetails.timezone || "UTC",
      },
      // Yellow color for activities
      colorId: "5",
      reminders: {
        useDefault: false,
        overrides: [
          { method: "popup", minutes: 60 }, // 1 hour before
        ],
      },
    };

    try {
      const response = await calendar.events.insert({
        calendarId: "primary",
        resource: event,
      });

      // Store mapping between activity and calendar event
      await db.collection("calendar_events").insertOne({
        userId,
        eventType: "activity",
        bookingId:
          activityDetails.bookingId ||
          activityDetails.confirmationCode ||
          activityDetails.name,
        eventId: response.data.id,
        created: new Date(),
      });

      return response.data;
    } catch (error) {
      console.error("Error adding activity to calendar:", error);
      throw new Error(`Failed to add activity to calendar: ${error.message}`);
    }
  }

  /**
   * Create complete travel itinerary in calendar
   * @param {string} userId User identifier
   * @param {Object} tripDetails Complete trip details
   * @returns {Promise<Object>} Created calendar events
   */
  async createTravelItinerary(userId, tripDetails) {
    // Create individual events for each itinerary item
    const events = [];

    try {
      // Process flights
      if (tripDetails.flights && tripDetails.flights.length > 0) {
        for (const flight of tripDetails.flights) {
          const event = await this.addFlightToCalendar(userId, flight);
          events.push({ type: "flight", event });
        }
      }

      // Process accommodations
      if (tripDetails.accommodations && tripDetails.accommodations.length > 0) {
        for (const accommodation of tripDetails.accommodations) {
          const event = await this.addAccommodationToCalendar(
            userId,
            accommodation
          );
          events.push({ type: "accommodation", event });
        }
      }

      // Process activities
      if (tripDetails.activities && tripDetails.activities.length > 0) {
        for (const activity of tripDetails.activities) {
          const event = await this.addActivityToCalendar(userId, activity);
          events.push({ type: "activity", event });
        }
      }

      return {
        tripId: tripDetails.tripId,
        events,
      };
    } catch (error) {
      console.error("Error creating travel itinerary:", error);
      throw new Error(`Failed to create travel itinerary: ${error.message}`);
    }
  }

  /**
   * Update an existing calendar event
   * @param {string} userId User identifier
   * @param {string} eventId Calendar event ID
   * @param {Object} updates Event updates
   * @returns {Promise<Object>} Updated event
   */
  async updateCalendarEvent(userId, eventId, updates) {
    const calendar = await this.getCalendarClient(userId);

    try {
      // First get the current event
      const currentEvent = await calendar.events.get({
        calendarId: "primary",
        eventId,
      });

      // Merge with updates
      const updatedEvent = {
        ...currentEvent.data,
        ...updates,
      };

      // Update the event
      const response = await calendar.events.update({
        calendarId: "primary",
        eventId,
        resource: updatedEvent,
      });

      return response.data;
    } catch (error) {
      console.error(`Error updating calendar event ${eventId}:`, error);
      throw new Error(`Failed to update calendar event: ${error.message}`);
    }
  }

  /**
   * Delete a calendar event
   * @param {string} userId User identifier
   * @param {string} eventId Calendar event ID
   * @returns {Promise<boolean>} Success status
   */
  async deleteCalendarEvent(userId, eventId) {
    const calendar = await this.getCalendarClient(userId);

    try {
      await calendar.events.delete({
        calendarId: "primary",
        eventId,
      });

      // Remove from mapping table
      await db.collection("calendar_events").deleteOne({
        userId,
        eventId,
      });

      return true;
    } catch (error) {
      console.error(`Error deleting calendar event ${eventId}:`, error);
      throw new Error(`Failed to delete calendar event: ${error.message}`);
    }
  }

  /**
   * List upcoming events in user's calendar
   * @param {string} userId User identifier
   * @param {number} maxResults Maximum number of events to return
   * @returns {Promise<Array>} Calendar events
   */
  async listUpcomingEvents(userId, maxResults = 10) {
    const calendar = await this.getCalendarClient(userId);

    try {
      const response = await calendar.events.list({
        calendarId: "primary",
        timeMin: new Date().toISOString(),
        maxResults: maxResults,
        singleEvents: true,
        orderBy: "startTime",
      });

      return response.data.items;
    } catch (error) {
      console.error("Error listing upcoming events:", error);
      throw new Error(`Failed to list upcoming events: ${error.message}`);
    }
  }

  /**
   * Export trip as calendar file (iCal format)
   * @param {string} userId User identifier
   * @param {string} tripId Trip identifier
   * @returns {Promise<string>} iCal file content
   */
  async exportTripAsICalendar(userId, tripId) {
    // This is a simplified implementation
    // In a real application, you would use a library like ical-generator

    try {
      // Get all events for this trip
      const eventRecords = await db
        .collection("calendar_events")
        .find({
          userId,
          tripId,
        })
        .toArray();

      if (!eventRecords || eventRecords.length === 0) {
        throw new Error("No calendar events found for this trip");
      }

      const calendar = await this.getCalendarClient(userId);

      // Fetch event details for each record
      const eventDetails = await Promise.all(
        eventRecords.map(async (record) => {
          const response = await calendar.events.get({
            calendarId: "primary",
            eventId: record.eventId,
          });

          return response.data;
        })
      );

      // Generate iCal content (simplified)
      const icalContent = this._generateICalContent(eventDetails);

      return icalContent;
    } catch (error) {
      console.error(`Error exporting trip ${tripId} as iCal:`, error);
      throw new Error(`Failed to export trip as iCal: ${error.message}`);
    }
  }

  /**
   * Generate iCal content from events (simplified implementation)
   * @private
   * @param {Array} events Calendar events
   * @returns {string} iCal content
   */
  _generateICalContent(events) {
    // This is a simplified implementation
    // In a real application, you would use a library like ical-generator

    let icalContent = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//TripSage//EN",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
    ];

    for (const event of events) {
      icalContent = icalContent.concat([
        "BEGIN:VEVENT",
        `UID:${event.id}`,
        `SUMMARY:${event.summary}`,
        `LOCATION:${event.location || ""}`,
        `DESCRIPTION:${event.description?.replace(/\n/g, "\\n") || ""}`,
        `DTSTART:${this._formatICalDate(event.start)}`,
        `DTEND:${this._formatICalDate(event.end)}`,
        "END:VEVENT",
      ]);
    }

    icalContent.push("END:VCALENDAR");

    return icalContent.join("\r\n");
  }

  /**
   * Format date for iCal (simplified)
   * @private
   * @param {Object} dateObj Date object from Google Calendar
   * @returns {string} Formatted date string
   */
  _formatICalDate(dateObj) {
    if (dateObj.date) {
      // All-day event
      return dateObj.date.replace(/-/g, "");
    } else if (dateObj.dateTime) {
      // Timed event
      return dateObj.dateTime
        .replace(/-/g, "")
        .replace(/:/g, "")
        .replace(/\.\d+/g, "")
        .replace(/Z$/, "Z");
    }

    return "";
  }
}

module.exports = new GoogleCalendarService();
```

### 2. Create API Endpoints

Create a file `src/api/routes/calendar.js`:

```javascript
const express = require("express");
const router = express.Router();
const googleCalendarService = require("../../services/calendar/google-calendar-service");
const { asyncHandler } = require("../../utils/error");

/**
 * @route   GET /api/calendar/auth
 * @desc    Get Google Calendar authorization URL
 * @access  Private
 */
router.get(
  "/auth",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;

    const authUrl = googleCalendarService.getAuthUrl(userId);

    res.json({ authUrl });
  })
);

/**
 * @route   GET /api/calendar/callback
 * @desc    Handle Google OAuth callback
 * @access  Public
 */
router.get(
  "/callback",
  asyncHandler(async (req, res) => {
    const { code, state } = req.query;

    if (!code || !state) {
      return res.status(400).json({ error: "Missing required parameters" });
    }

    try {
      const result = await googleCalendarService.handleCallback(code, state);

      // Redirect to frontend with success message
      res.redirect(`/calendar/success?userId=${result.userId}`);
    } catch (error) {
      console.error("OAuth callback error:", error);

      // Redirect to frontend with error message
      res.redirect(
        `/calendar/error?message=${encodeURIComponent(error.message)}`
      );
    }
  })
);

/**
 * @route   POST /api/calendar/flight
 * @desc    Add flight to calendar
 * @access  Private
 */
router.post(
  "/flight",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const flightDetails = req.body;

    // Validate required parameters
    if (
      !flightDetails.airline ||
      !flightDetails.flightNumber ||
      !flightDetails.departureTime ||
      !flightDetails.arrivalTime ||
      !flightDetails.departureAirport ||
      !flightDetails.arrivalAirport
    ) {
      return res.status(400).json({
        error: "Missing required flight details",
      });
    }

    const event = await googleCalendarService.addFlightToCalendar(
      userId,
      flightDetails
    );

    res.status(201).json(event);
  })
);

/**
 * @route   POST /api/calendar/accommodation
 * @desc    Add accommodation to calendar
 * @access  Private
 */
router.post(
  "/accommodation",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const accommodationDetails = req.body;

    // Validate required parameters
    if (
      !accommodationDetails.propertyName ||
      !accommodationDetails.checkInDate ||
      !accommodationDetails.checkOutDate ||
      !accommodationDetails.address
    ) {
      return res.status(400).json({
        error: "Missing required accommodation details",
      });
    }

    const event = await googleCalendarService.addAccommodationToCalendar(
      userId,
      accommodationDetails
    );

    res.status(201).json(event);
  })
);

/**
 * @route   POST /api/calendar/activity
 * @desc    Add activity to calendar
 * @access  Private
 */
router.post(
  "/activity",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const activityDetails = req.body;

    // Validate required parameters
    if (
      !activityDetails.name ||
      !activityDetails.startTime ||
      !activityDetails.endTime ||
      !activityDetails.location
    ) {
      return res.status(400).json({
        error: "Missing required activity details",
      });
    }

    const event = await googleCalendarService.addActivityToCalendar(
      userId,
      activityDetails
    );

    res.status(201).json(event);
  })
);

/**
 * @route   POST /api/calendar/itinerary
 * @desc    Create full travel itinerary in calendar
 * @access  Private
 */
router.post(
  "/itinerary",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const tripDetails = req.body;

    // Validate required parameters
    if (!tripDetails.tripId) {
      return res.status(400).json({
        error: "Missing trip identifier",
      });
    }

    const result = await googleCalendarService.createTravelItinerary(
      userId,
      tripDetails
    );

    res.status(201).json(result);
  })
);

/**
 * @route   GET /api/calendar/events
 * @desc    List upcoming calendar events
 * @access  Private
 */
router.get(
  "/events",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const maxResults = req.query.limit ? parseInt(req.query.limit, 10) : 10;

    const events = await googleCalendarService.listUpcomingEvents(
      userId,
      maxResults
    );

    res.json(events);
  })
);

/**
 * @route   PUT /api/calendar/events/:eventId
 * @desc    Update a calendar event
 * @access  Private
 */
router.put(
  "/events/:eventId",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const eventId = req.params.eventId;
    const updates = req.body;

    const updatedEvent = await googleCalendarService.updateCalendarEvent(
      userId,
      eventId,
      updates
    );

    res.json(updatedEvent);
  })
);

/**
 * @route   DELETE /api/calendar/events/:eventId
 * @desc    Delete a calendar event
 * @access  Private
 */
router.delete(
  "/events/:eventId",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const eventId = req.params.eventId;

    await googleCalendarService.deleteCalendarEvent(userId, eventId);

    res.status(204).end();
  })
);

/**
 * @route   GET /api/calendar/export/:tripId
 * @desc    Export trip as iCal file
 * @access  Private
 */
router.get(
  "/export/:tripId",
  asyncHandler(async (req, res) => {
    const userId = req.user.id;
    const tripId = req.params.tripId;

    const icalContent = await googleCalendarService.exportTripAsICalendar(
      userId,
      tripId
    );

    res.set("Content-Type", "text/calendar");
    res.set("Content-Disposition", `attachment; filename="trip-${tripId}.ics"`);
    res.send(icalContent);
  })
);

module.exports = router;
```

### 3. Add to API Gateway

Update `src/api/index.js` to include the calendar routes:

```javascript
// Add this line with the other route imports
const calendarRoutes = require("./routes/calendar");

// Add this line with the other app.use statements
app.use("/api/calendar", calendarRoutes);
```

### 4. Calendar Integration Utilities

Create a file `src/utils/calendar-utils.js`:

```javascript
/**
 * Utility functions for calendar operations
 */
const calendarUtils = {
  /**
   * Format date for calendar display
   * @param {Date|string} date Date to format
   * @param {string} format Output format
   * @returns {string} Formatted date string
   */
  formatDate(date, format = "YYYY-MM-DD") {
    const d = typeof date === "string" ? new Date(date) : date;

    // Handle invalid dates
    if (isNaN(d.getTime())) {
      return "Invalid date";
    }

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");

    // Replace format tokens
    return format
      .replace("YYYY", year)
      .replace("MM", month)
      .replace("DD", day)
      .replace("HH", hours)
      .replace("mm", minutes);
  },

  /**
   * Generate color coding for different event types
   * @param {string} eventType Type of event
   * @returns {string} Google Calendar color ID
   */
  getColorForEventType(eventType) {
    const colorMap = {
      flight: "1", // Blue
      accommodation: "2", // Green
      activity: "5", // Yellow
      transport: "7", // Purple
      meeting: "3", // Purple
      dining: "10", // Red
      sightseeing: "6", // Orange
      generic: "8", // Gray
    };

    return colorMap[eventType] || colorMap.generic;
  },

  /**
   * Calculate travel buffer times for transportation events
   * @param {Object} transportDetails Transportation details
   * @returns {Object} Buffer times in minutes
   */
  calculateTravelBuffers(transportDetails) {
    // Default buffers
    const buffers = {
      before: 0,
      after: 0,
    };

    // For flights, add appropriate buffer times
    if (transportDetails.type === "flight") {
      if (transportDetails.international) {
        buffers.before = 180; // 3 hours before international flights
      } else {
        buffers.before = 120; // 2 hours before domestic flights
      }
      buffers.after = 60; // 1 hour after landing for baggage claim, etc.
    }
    // For trains
    else if (transportDetails.type === "train") {
      buffers.before = 45; // 45 minutes before train
      buffers.after = 30; // 30 minutes after arrival
    }
    // For buses
    else if (transportDetails.type === "bus") {
      buffers.before = 30; // 30 minutes before bus
      buffers.after = 15; // 15 minutes after arrival
    }

    return buffers;
  },

  /**
   * Generate smart reminders for travel events
   * @param {Object} eventDetails Event details
   * @returns {Array} Reminder configuration
   */
  generateSmartReminders(eventDetails) {
    const reminders = [];

    // Standard reminder for all events
    reminders.push({ method: "popup", minutes: 60 }); // 1 hour before

    // Event-specific reminders
    switch (eventDetails.type) {
      case "flight":
        // Check-in reminder (usually 24 hours before)
        if (eventDetails.checkInTime) {
          const checkInMinutes = Math.floor(
            (new Date(eventDetails.startTime) -
              new Date(eventDetails.checkInTime)) /
              60000
          );
          if (checkInMinutes > 0) {
            reminders.push({ method: "email", minutes: checkInMinutes });
          }
        } else {
          // Default check-in reminder (24 hours)
          reminders.push({ method: "email", minutes: 24 * 60 });
        }

        // Airport travel time reminder
        reminders.push({ method: "popup", minutes: 3 * 60 }); // 3 hours before
        break;

      case "accommodation":
        // Check-in reminder
        reminders.push({ method: "email", minutes: 24 * 60 }); // 24 hours before

        // Day-of reminder
        reminders.push({ method: "popup", minutes: 3 * 60 }); // 3 hours before
        break;

      case "activity":
        // Activity preparation reminder
        reminders.push({ method: "popup", minutes: 3 * 60 }); // 3 hours before
        break;
    }

    return reminders;
  },
};

module.exports = calendarUtils;
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

Create a file `src/tests/google-calendar-service.test.js`:

```javascript
const googleCalendarService = require("../services/calendar/google-calendar-service");
const { v4: uuidv4 } = require("uuid");
const db = require("../utils/db");

// Mock user for testing
const testUserId = `test-${uuidv4()}`;

async function testGoogleCalendarService() {
  try {
    // Skip tests if no valid tokens are available
    const tokens = await googleCalendarService.getUserTokens(testUserId);
    if (!tokens) {
      console.log("No valid tokens available. Run authorization flow first.");
      return true;
    }

    console.log("Testing flight calendar event creation...");
    const flightEvent = await googleCalendarService.addFlightToCalendar(
      testUserId,
      {
        airline: "TEST",
        flightNumber: "123",
        departureAirport: "JFK",
        arrivalAirport: "LAX",
        departureTime: new Date(
          Date.now() + 7 * 24 * 60 * 60 * 1000
        ).toISOString(), // 7 days from now
        arrivalTime: new Date(
          Date.now() + 7 * 24 * 60 * 60 * 1000 + 6 * 60 * 60 * 1000
        ).toISOString(), // 6 hours later
        departureTerminal: "T4",
        arrivalTerminal: "T2",
        confirmationCode: "ABC123",
        status: "Confirmed",
      }
    );
    console.log("Flight event created:", flightEvent.id);

    console.log("Testing accommodation calendar event creation...");
    const accommodationEvent =
      await googleCalendarService.addAccommodationToCalendar(testUserId, {
        propertyName: "Test Hotel",
        address: "123 Test Street, Test City, TC 12345",
        checkInDate: new Date(
          Date.now() + 7 * 24 * 60 * 60 * 1000
        ).toISOString(), // 7 days from now
        checkOutDate: new Date(
          Date.now() + 10 * 24 * 60 * 60 * 1000
        ).toISOString(), // 3 days stay
        confirmationCode: "DEF456",
        roomType: "Deluxe Room",
        guests: 2,
      });
    console.log("Accommodation event created:", accommodationEvent.id);

    console.log("Testing activity calendar event creation...");
    const activityEvent = await googleCalendarService.addActivityToCalendar(
      testUserId,
      {
        name: "Test Tour",
        location: "Tour Meeting Point, Test City",
        startTime: new Date(Date.now() + 8 * 24 * 60 * 60 * 1000).toISOString(), // 8 days from now
        endTime: new Date(
          Date.now() + 8 * 24 * 60 * 60 * 1000 + 3 * 60 * 60 * 1000
        ).toISOString(), // 3 hours later
        confirmationCode: "GHI789",
        participants: 2,
      }
    );
    console.log("Activity event created:", activityEvent.id);

    console.log("Testing event listing...");
    const events = await googleCalendarService.listUpcomingEvents(
      testUserId,
      5
    );
    console.log(`Found ${events.length} upcoming events`);

    // Clean up test events
    console.log("Cleaning up test events...");
    await googleCalendarService.deleteCalendarEvent(testUserId, flightEvent.id);
    await googleCalendarService.deleteCalendarEvent(
      testUserId,
      accommodationEvent.id
    );
    await googleCalendarService.deleteCalendarEvent(
      testUserId,
      activityEvent.id
    );
    console.log("Test events deleted");

    return true;
  } catch (error) {
    console.error("Test failed:", error);
    return false;
  }
}

// Run test
testGoogleCalendarService().then((success) => {
  if (success) {
    console.log("\nAll Google Calendar tests passed!");
  } else {
    console.error("\nGoogle Calendar tests failed");
    process.exit(1);
  }
});
```

### Integration Testing

Test the following scenarios:

1. **Authorization Flow**:

   - Test the OAuth authorization URL generation
   - Test the OAuth callback handling
   - Verify token storage and retrieval
   - Test token refresh logic

2. **Flight Event Creation**:

   - Test with various flight details
   - Verify correct time zone handling
   - Check reminder settings
   - Validate event metadata

3. **Accommodation Event Creation**:

   - Test with different check-in/check-out patterns
   - Verify all-day event creation
   - Check property information inclusion
   - Validate event metadata

4. **Activity Event Creation**:

   - Test with different activity types
   - Verify time-bound event creation
   - Check location and description formatting
   - Validate event metadata

5. **Complete Itinerary Creation**:
   - Test creating multiple events in sequence
   - Verify correct event ordering
   - Check cross-references between events
   - Validate export functionality

## Advanced Features

### 1. Shared Calendars for Group Travel

```javascript
// Add to GoogleCalendarService class
/**
 * Create a shared calendar for a group trip
 * @param {string} userId User identifier
 * @param {Object} tripDetails Trip details
 * @param {Array} participants Participant email addresses
 * @returns {Promise<Object>} Created calendar details
 */
async createSharedTripCalendar(userId, tripDetails, participants) {
  const calendar = await this.getCalendarClient(userId);

  try {
    // Create a new calendar for the trip
    const newCalendar = await calendar.calendars.insert({
      resource: {
        summary: `Trip: ${tripDetails.destination}`,
        description: `Travel itinerary for trip to ${tripDetails.destination} from ${tripDetails.startDate} to ${tripDetails.endDate}`,
        timeZone: tripDetails.timezone || 'UTC'
      }
    });

    // Share the calendar with participants
    for (const email of participants) {
      await calendar.acl.insert({
        calendarId: newCalendar.data.id,
        resource: {
          role: 'reader',
          scope: {
            type: 'user',
            value: email
          }
        }
      });
    }

    // Add trip events to the shared calendar
    const events = [];

    // Process flights
    if (tripDetails.flights && tripDetails.flights.length > 0) {
      for (const flight of tripDetails.flights) {
        const event = await this._addEventToCalendar(
          calendar,
          newCalendar.data.id,
          this._createFlightEvent(flight)
        );
        events.push({ type: 'flight', event });
      }
    }

    // Process accommodations and activities similarly...

    return {
      calendarId: newCalendar.data.id,
      calendarName: newCalendar.data.summary,
      events,
      sharedWith: participants
    };
  } catch (error) {
    console.error('Error creating shared trip calendar:', error);
    throw new Error(`Failed to create shared trip calendar: ${error.message}`);
  }
}

/**
 * Helper method to add an event to a specific calendar
 * @private
 */
async _addEventToCalendar(calendarClient, calendarId, eventResource) {
  const response = await calendarClient.events.insert({
    calendarId: calendarId,
    resource: eventResource
  });

  return response.data;
}
```

### 2. Smart Travel Reminders

```javascript
// Add to GoogleCalendarService class
/**
 * Add smart travel reminders based on trip context
 * @param {string} userId User identifier
 * @param {string} tripId Trip identifier
 * @returns {Promise<Array>} Created reminder events
 */
async addSmartTravelReminders(userId, tripId) {
  const calendar = await this.getCalendarClient(userId);

  try {
    // Get all events for this trip
    const tripEvents = await db.collection('calendar_events').find({
      userId,
      tripId
    }).toArray();

    if (!tripEvents || tripEvents.length === 0) {
      throw new Error('No calendar events found for this trip');
    }

    // Get event details
    const eventDetails = await Promise.all(
      tripEvents.map(async (record) => {
        const response = await calendar.events.get({
          calendarId: 'primary',
          eventId: record.eventId
        });

        return {
          ...response.data,
          type: record.eventType
        };
      })
    );

    // Sort events by start time
    eventDetails.sort((a, b) => {
      const aTime = a.start.dateTime ? new Date(a.start.dateTime).getTime() : new Date(a.start.date).getTime();
      const bTime = b.start.dateTime ? new Date(b.start.dateTime).getTime() : new Date(b.start.date).getTime();
      return aTime - bTime;
    });

    const reminders = [];

    // Add pre-trip reminders
    const firstEvent = eventDetails[0];
    const tripStartTime = firstEvent.start.dateTime ? new Date(firstEvent.start.dateTime) : new Date(firstEvent.start.date);

    // Passport reminder (7 days before trip)
    const passportReminderDate = new Date(tripStartTime);
    passportReminderDate.setDate(passportReminderDate.getDate() - 7);

    const passportReminder = await calendar.events.insert({
      calendarId: 'primary',
      resource: {
        summary: 'Check Passport and Travel Documents',
        description: 'Make sure your passport, visa, and other travel documents are ready for your upcoming trip.',
        start: {
          dateTime: passportReminderDate.toISOString()
        },
        end: {
          dateTime: new Date(passportReminderDate.getTime() + 30 * 60000).toISOString()
        },
        reminders: {
          useDefault: false,
          overrides: [
            { method: 'popup', minutes: 60 * 24 } // 1 day before
          ]
        }
      }
    });

    reminders.push(passportReminder.data);

    // Packing reminder (2 days before trip)
    const packingReminderDate = new Date(tripStartTime);
    packingReminderDate.setDate(packingReminderDate.getDate() - 2);

    const packingReminder = await calendar.events.insert({
      calendarId: 'primary',
      resource: {
        summary: 'Pack for Your Trip',
        description: 'Time to pack for your upcoming trip. Don\'t forget essentials like chargers, medications, and travel documents.',
        start: {
          dateTime: packingReminderDate.toISOString()
        },
        end: {
          dateTime: new Date(packingReminderDate.getTime() + 30 * 60000).toISOString()
        },
        reminders: {
          useDefault: false,
          overrides: [
            { method: 'popup', minutes: 60 * 12 } // 12 hours before
          ]
        }
      }
    });

    reminders.push(packingReminder.data);

    // Add additional smart reminders based on event types
    for (const event of eventDetails) {
      if (event.type === 'flight') {
        // Online check-in reminder (24 hours before flight if international, else 48 hours)
        // Airport transportation reminder
        // etc.
      } else if (event.type === 'accommodation') {
        // Check-out reminder
        // Payment reminder if applicable
        // etc.
      }
    }

    return reminders;
  } catch (error) {
    console.error(`Error adding smart reminders for trip ${tripId}:`, error);
    throw new Error(`Failed to add smart reminders: ${error.message}`);
  }
}
```

### 3. Calendar Integration with Weather Data

```javascript
// Add to GoogleCalendarService class
/**
 * Enhance calendar events with weather data
 * @param {string} userId User identifier
 * @param {string} tripId Trip identifier
 * @returns {Promise<Array>} Updated events
 */
async enhanceEventsWithWeather(userId, tripId) {
  const weatherService = require('../weather/weather-service'); // Import weather service
  const calendar = await this.getCalendarClient(userId);

  try {
    // Get all events for this trip
    const tripEvents = await db.collection('calendar_events').find({
      userId,
      tripId
    }).toArray();

    if (!tripEvents || tripEvents.length === 0) {
      throw new Error('No calendar events found for this trip');
    }

    const updatedEvents = [];

    // Process each event
    for (const record of tripEvents) {
      // Get event details
      const event = await calendar.events.get({
        calendarId: 'primary',
        eventId: record.eventId
      });

      // Skip events too far in the future (beyond weather forecast range)
      const eventDate = event.data.start.dateTime
        ? new Date(event.data.start.dateTime)
        : new Date(event.data.start.date);

      const now = new Date();
      const daysDifference = Math.floor((eventDate - now) / (1000 * 60 * 60 * 24));

      // Only enhance events within the 5-day forecast window
      if (daysDifference <= 5) {
        let location = event.data.location;

        if (location) {
          // Extract city from location
          const cityMatch = location.match(/(?:^|,\s*)([^,]+)(?:,|$)/);
          const city = cityMatch ? cityMatch[1].trim() : location;

          // Get weather forecast for the location and date
          try {
            const forecast = await weatherService.getForecast(city);

            // Find forecast for event date
            const eventDateString = eventDate.toISOString().split('T')[0];
            const dayForecast = forecast.daily_forecast.find(day => day.date === eventDateString);

            if (dayForecast) {
              // Append weather info to event description
              const weatherInfo = `\n\nWEATHER FORECAST:
Temperature: ${dayForecast.temperature.min}°C to ${dayForecast.temperature.max}°C
Conditions: ${dayForecast.condition.main}
${dayForecast.travel_advice ? `Travel Advice: ${dayForecast.travel_advice.join(', ')}` : ''}`;

              const updatedDescription = event.data.description + weatherInfo;

              // Update the event
              const updatedEvent = await calendar.events.patch({
                calendarId: 'primary',
                eventId: event.data.id,
                resource: {
                  description: updatedDescription
                }
              });

              updatedEvents.push(updatedEvent.data);
            }
          } catch (weatherError) {
            console.log(`Could not get weather for ${city}:`, weatherError.message);
          }
        }
      }
    }

    return updatedEvents;
  } catch (error) {
    console.error(`Error enhancing events with weather for trip ${tripId}:`, error);
    throw new Error(`Failed to enhance events with weather: ${error.message}`);
  }
}
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:

   - Verify that OAuth credentials are correct
   - Check that redirect URIs match exactly
   - Ensure scopes are properly configured
   - Verify that OAuth consent screen is properly set up

2. **Token Expiration Issues**:

   - Implement token refresh logic
   - Store refresh tokens securely
   - Handle refresh token errors by prompting for re-authorization

3. **Calendar Event Creation Failures**:

   - Validate all required fields
   - Check for formatting issues in dates and times
   - Ensure time zones are properly specified
   - Verify the user has write permission to their calendar

4. **Event Synchronization Problems**:
   - Implement error detection and retry logic
   - Store event IDs for later reference
   - Add transaction-like patterns for complex operations

### Error Handling

To gracefully handle API errors:

1. Wrap all API calls in try/catch blocks
2. Implement specific error handling for different error types
3. Add retry logic with exponential backoff for transient errors
4. Log detailed error information for debugging
5. Provide user-friendly error messages

## Implementation Checklist

- [ ] Create Google Cloud project and enable Calendar API
- [ ] Configure OAuth consent screen and create credentials
- [ ] Set up environment variables for API keys
- [ ] Implement GoogleCalendarService class
- [ ] Create OAuth authentication flow
- [ ] Implement token storage and refresh mechanism
- [ ] Add calendar event creation methods for different travel items
- [ ] Create API endpoints for calendar operations
- [ ] Implement security best practices
- [ ] Add unit and integration tests
- [ ] Create documentation for developers
- [ ] Add advanced features (optional)

## Integration with Other TripSage Components

The calendar integration works seamlessly with other TripSage features:

1. **Flight Booking**: After booking a flight, offer to add it to the user's calendar
2. **Accommodation Booking**: Add hotel stays as all-day events with check-in/out details
3. **Activity Planning**: Sync planned activities with appropriate reminders
4. **Weather Integration**: Enhance calendar events with weather forecasts
5. **Itinerary Management**: Provide a comprehensive calendar view of the entire trip

By following this implementation guide, you'll have a robust Google Calendar integration that enhances the travel planning experience with comprehensive itinerary management while supporting personal use with individual Google accounts.
