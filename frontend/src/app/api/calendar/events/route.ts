/**
 * @fileoverview Calendar events CRUD endpoint.
 *
 * Handles GET (list), POST (create), PATCH (update), and DELETE operations
 * for calendar events.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import {
  createEventRequestSchema,
  eventsListRequestSchema,
  updateEventRequestSchema,
} from "@schemas/calendar";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, validateSchema } from "@/lib/api/route-helpers";
import {
  createEvent,
  deleteEvent,
  listEvents,
  updateEvent,
} from "@/lib/calendar/google";

/**
 * Extracts calendar ID from body or query params with default fallback.
 *
 * @param source Source object (body or searchParams).
 * @param key Key to extract (defaults to "calendarId").
 * @returns Calendar ID string.
 */
function getCalendarId(
  source: Record<string, unknown> | URLSearchParams,
  key = "calendarId"
): string {
  const value =
    source instanceof URLSearchParams
      ? source.get(key)
      : (source[key] as string | undefined);
  return value || "primary";
}

/**
 * GET /api/calendar/events
 *
 * List events from a calendar.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with events list
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "calendar:events:read",
  telemetry: "calendar.events.list",
})(async (req: NextRequest) => {
  // Parse query parameters
  const { searchParams } = new URL(req.url);
  const params: Record<string, unknown> = {
    calendarId: searchParams.get("calendarId") || "primary",
  };

  const timeMinValue = searchParams.get("timeMin");
  if (timeMinValue) {
    params.timeMin = new Date(timeMinValue);
  }
  const timeMaxValue = searchParams.get("timeMax");
  if (timeMaxValue) {
    params.timeMax = new Date(timeMaxValue);
  }
  const maxResultsValue = searchParams.get("maxResults");
  if (maxResultsValue) {
    params.maxResults = Number.parseInt(maxResultsValue, 10);
  }
  if (searchParams.get("orderBy")) {
    params.orderBy = searchParams.get("orderBy");
  }
  if (searchParams.get("pageToken")) {
    params.pageToken = searchParams.get("pageToken");
  }
  if (searchParams.get("q")) {
    params.q = searchParams.get("q");
  }
  if (searchParams.get("timeZone")) {
    params.timeZone = searchParams.get("timeZone");
  }
  if (searchParams.get("singleEvents") === "true") {
    params.singleEvents = true;
  }
  if (searchParams.get("showDeleted") === "true") {
    params.showDeleted = true;
  }

  const validation = validateSchema(eventsListRequestSchema, params);
  if ("error" in validation) {
    return validation.error;
  }
  const result = await listEvents(validation.data);

  return NextResponse.json(result);
});

/**
 * POST /api/calendar/events
 *
 * Create a new calendar event.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with created event
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "calendar:events:create",
  telemetry: "calendar.events.create",
})(async (req: NextRequest) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const typedBody = parsed.body as Record<string, unknown>;
  const calendarId = getCalendarId(typedBody);

  const validation = validateSchema(createEventRequestSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const result = await createEvent(validation.data, calendarId);

  return NextResponse.json(result, { status: 201 });
});

/**
 * PATCH /api/calendar/events?eventId=...&calendarId=...
 *
 * Update an existing calendar event.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with updated event
 */
export const PATCH = withApiGuards({
  auth: true,
  rateLimit: "calendar:events:update",
  telemetry: "calendar.events.update",
})(async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const eventId = searchParams.get("eventId");
  const calendarId = getCalendarId(searchParams);

  if (!eventId) {
    return NextResponse.json(
      { error: "eventId query parameter is required" },
      { status: 400 }
    );
  }

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(updateEventRequestSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const result = await updateEvent(eventId, validation.data, calendarId);

  return NextResponse.json(result);
});

/**
 * DELETE /api/calendar/events?eventId=...&calendarId=...
 *
 * Delete a calendar event.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with success status
 */
export const DELETE = withApiGuards({
  auth: true,
  rateLimit: "calendar:events:delete",
  telemetry: "calendar.events.delete",
})(async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const eventId = searchParams.get("eventId");
  const calendarId = getCalendarId(searchParams);

  if (!eventId) {
    return NextResponse.json(
      { error: "eventId query parameter is required" },
      { status: 400 }
    );
  }

  await deleteEvent(eventId, calendarId);

  return NextResponse.json({ success: true }, { status: 200 });
});
