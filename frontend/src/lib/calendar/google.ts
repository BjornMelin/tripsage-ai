/**
 * @fileoverview Google Calendar REST API v3 client wrapper.
 *
 * Thin wrapper around Google Calendar REST API using Supabase OAuth tokens.
 * All methods require server-side execution and authenticated user sessions.
 */

import "server-only";

import type {
  CalendarEvent,
  CalendarList,
  CreateEventRequest,
  EventsListRequest,
  EventsListResponse,
  FreeBusyRequest,
  FreeBusyResponse,
  UpdateEventRequest,
} from "@/lib/schemas/calendar";
import { getGoogleProviderToken } from "./auth";

const GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3";

/**
 * Error thrown when Google Calendar API request fails.
 */
export class GoogleCalendarApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: unknown
  ) {
    super(message);
    this.name = "GoogleCalendarApiError";
  }
}

/**
 * Make authenticated request to Google Calendar API.
 *
 * @param endpoint - API endpoint (relative to base URL)
 * @param options - Fetch options (method, body, etc.)
 * @returns Promise resolving to JSON response
 * @throws GoogleCalendarApiError on API errors
 */
async function googleCalendarRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getGoogleProviderToken();
  const url = `${GOOGLE_CALENDAR_API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      // biome-ignore lint/style/useNamingConvention: HTTP header name
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    let errorData: unknown;
    try {
      errorData = JSON.parse(errorText);
    } catch {
      errorData = errorText;
    }

    throw new GoogleCalendarApiError(
      `Google Calendar API error: ${response.status} ${response.statusText}`,
      response.status,
      errorData
    );
  }

  return response.json() as Promise<T>;
}

/**
 * Get list of calendars for the authenticated user.
 *
 * @returns Promise resolving to calendar list
 */
export function listCalendars(): Promise<CalendarList> {
  return googleCalendarRequest<CalendarList>("/users/me/calendarList");
}

/**
 * Get calendar details by ID.
 *
 * @param calendarId - Calendar ID (default: "primary")
 * @returns Promise resolving to calendar details
 */
export function getCalendar(
  calendarId: string = "primary"
): Promise<CalendarList["items"][number]> {
  return googleCalendarRequest(`/calendars/${encodeURIComponent(calendarId)}`);
}

/**
 * List events from a calendar.
 *
 * @param params - Event list parameters
 * @returns Promise resolving to events list response
 */
export function listEvents(params: EventsListRequest): Promise<EventsListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("calendarId", params.calendarId || "primary");

  if (params.timeMin) {
    searchParams.set("timeMin", params.timeMin.toISOString());
  }
  if (params.timeMax) {
    searchParams.set("timeMax", params.timeMax.toISOString());
  }
  if (params.maxResults) {
    searchParams.set("maxResults", String(params.maxResults));
  }
  if (params.orderBy) {
    searchParams.set("orderBy", params.orderBy);
  }
  if (params.pageToken) {
    searchParams.set("pageToken", params.pageToken);
  }
  if (params.q) {
    searchParams.set("q", params.q);
  }
  if (params.timeZone) {
    searchParams.set("timeZone", params.timeZone);
  }
  if (params.singleEvents) {
    searchParams.set("singleEvents", "true");
  }
  if (params.showDeleted) {
    searchParams.set("showDeleted", "true");
  }

  const queryString = searchParams.toString();
  return googleCalendarRequest<EventsListResponse>(
    `/calendars/${encodeURIComponent(params.calendarId || "primary")}/events${
      queryString ? `?${queryString}` : ""
    }`
  );
}

/**
 * Get a specific event by ID.
 *
 * @param calendarId - Calendar ID (default: "primary")
 * @param eventId - Event ID
 * @returns Promise resolving to calendar event
 */
export function getEvent(
  eventId: string,
  calendarId: string = "primary"
): Promise<CalendarEvent> {
  return googleCalendarRequest<CalendarEvent>(
    `/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`
  );
}

/**
 * Create a new calendar event.
 *
 * @param calendarId - Calendar ID (default: "primary")
 * @param event - Event creation request
 * @returns Promise resolving to created calendar event
 */
export function createEvent(
  event: CreateEventRequest,
  calendarId: string = "primary"
): Promise<CalendarEvent> {
  // Convert Zod schema to Google Calendar API format
  const payload: Record<string, unknown> = {
    description: event.description,
    end: {
      ...(event.end.dateTime ? { dateTime: event.end.dateTime.toISOString() } : {}),
      ...(event.end.date ? { date: event.end.date } : {}),
      ...(event.end.timeZone ? { timeZone: event.end.timeZone } : {}),
    },
    location: event.location,
    start: {
      ...(event.start.dateTime ? { dateTime: event.start.dateTime.toISOString() } : {}),
      ...(event.start.date ? { date: event.start.date } : {}),
      ...(event.start.timeZone ? { timeZone: event.start.timeZone } : {}),
    },
    summary: event.summary,
    ...(event.timeZone ? { timeZone: event.timeZone } : {}),
    ...(event.attendees?.length ? { attendees: event.attendees } : {}),
    ...(event.reminders ? { reminders: event.reminders } : {}),
    ...(event.visibility ? { visibility: event.visibility } : {}),
    ...(event.transparency ? { transparency: event.transparency } : {}),
    ...(event.recurrence?.length ? { recurrence: event.recurrence } : {}),
    ...(event.conferenceDataVersion
      ? { conferenceDataVersion: event.conferenceDataVersion }
      : {}),
  };

  // Handle travel metadata via extended properties
  if (event.travelMetadata) {
    payload.extendedProperties = {
      private: {
        // biome-ignore lint/style/useNamingConvention: Private metadata field name
        tripsage_metadata: JSON.stringify(event.travelMetadata),
      },
    };
  }

  return googleCalendarRequest<CalendarEvent>(
    `/calendars/${encodeURIComponent(calendarId)}/events`,
    {
      body: JSON.stringify(payload),
      method: "POST",
    }
  );
}

/**
 * Update an existing calendar event.
 *
 * @param calendarId - Calendar ID (default: "primary")
 * @param eventId - Event ID
 * @param event - Event update request
 * @returns Promise resolving to updated calendar event
 */
export function updateEvent(
  eventId: string,
  event: UpdateEventRequest,
  calendarId: string = "primary"
): Promise<CalendarEvent> {
  const payload: Record<string, unknown> = {};

  if (event.summary !== undefined) payload.summary = event.summary;
  if (event.description !== undefined) payload.description = event.description;
  if (event.location !== undefined) payload.location = event.location;
  if (event.start) {
    payload.start = {
      ...(event.start.dateTime ? { dateTime: event.start.dateTime.toISOString() } : {}),
      ...(event.start.date ? { date: event.start.date } : {}),
      ...(event.start.timeZone ? { timeZone: event.start.timeZone } : {}),
    };
  }
  if (event.end) {
    payload.end = {
      ...(event.end.dateTime ? { dateTime: event.end.dateTime.toISOString() } : {}),
      ...(event.end.date ? { date: event.end.date } : {}),
      ...(event.end.timeZone ? { timeZone: event.end.timeZone } : {}),
    };
  }
  if (event.timeZone !== undefined) payload.timeZone = event.timeZone;
  if (event.attendees !== undefined) payload.attendees = event.attendees;
  if (event.reminders !== undefined) payload.reminders = event.reminders;
  if (event.visibility !== undefined) payload.visibility = event.visibility;
  if (event.transparency !== undefined) payload.transparency = event.transparency;
  if (event.recurrence !== undefined) payload.recurrence = event.recurrence;

  // Handle travel metadata via extended properties
  if (event.travelMetadata) {
    payload.extendedProperties = {
      private: {
        // biome-ignore lint/style/useNamingConvention: Private metadata field name
        tripsage_metadata: JSON.stringify(event.travelMetadata),
      },
    };
  }

  return googleCalendarRequest<CalendarEvent>(
    `/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`,
    {
      body: JSON.stringify(payload),
      method: "PATCH",
    }
  );
}

/**
 * Delete a calendar event.
 *
 * @param calendarId - Calendar ID (default: "primary")
 * @param eventId - Event ID
 * @returns Promise resolving when deletion completes
 */
export async function deleteEvent(
  eventId: string,
  calendarId: string = "primary"
): Promise<void> {
  await googleCalendarRequest(
    `/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`,
    {
      method: "DELETE",
    }
  );
}

/**
 * Query free/busy information for calendars.
 *
 * @param request - Free/busy query request
 * @returns Promise resolving to free/busy response
 */
export function queryFreeBusy(request: FreeBusyRequest): Promise<FreeBusyResponse> {
  const payload = {
    timeMax: request.timeMax.toISOString(),
    timeMin: request.timeMin.toISOString(),
    ...(request.timeZone ? { timeZone: request.timeZone } : {}),
    calendarExpansionMax: request.calendarExpansionMax,
    groupExpansionMax: request.groupExpansionMax,
    items: request.items,
  };

  return googleCalendarRequest<FreeBusyResponse>("/freeBusy", {
    body: JSON.stringify(payload),
    method: "POST",
  });
}
