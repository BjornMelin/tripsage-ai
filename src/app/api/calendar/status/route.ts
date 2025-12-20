/**
 * @fileoverview Calendar connection status endpoint.
 *
 * Returns connection status, granted scopes, and list of calendars for the
 * authenticated user.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { hasGoogleCalendarScopes } from "@/lib/calendar/auth";
import { GoogleCalendarApiError, listCalendars } from "@/lib/calendar/google";

/**
 * GET /api/calendar/status
 *
 * Get calendar connection status and list of calendars.
 *
 * @returns JSON response with calendar status and list
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "calendar:status",
  telemetry: "calendar.status",
})(async () => {
  // Check if user has Google Calendar scopes
  const hasScopes = await hasGoogleCalendarScopes();
  if (!hasScopes) {
    return NextResponse.json(
      {
        connected: false,
        message: "Google Calendar not connected. Please connect your Google account.",
      },
      { status: 200 }
    );
  }

  // Fetch calendar list
  try {
    const calendars = await listCalendars();
    return NextResponse.json({
      calendars: calendars.items.map((cal) => ({
        accessRole: cal.accessRole,
        description: cal.description,
        id: cal.id,
        primary: cal.primary,
        summary: cal.summary,
        timeZone: cal.timeZone,
      })),
      connected: true,
    });
  } catch (error) {
    // Use typed GoogleCalendarApiError for code-based handling
    if (error instanceof GoogleCalendarApiError) {
      // 401: Token expired or revoked
      if (error.statusCode === 401) {
        return NextResponse.json(
          {
            connected: false,
            message: "Google Calendar token expired. Please reconnect your account.",
          },
          { status: 200 }
        );
      }

      // 403: Insufficient scopes or access denied
      if (error.statusCode === 403) {
        return NextResponse.json(
          {
            connected: false,
            message: "Insufficient permissions. Please reconnect with calendar access.",
          },
          { status: 200 }
        );
      }

      // Other Google Calendar API errors
      return errorResponse({
        err: error,
        error: "calendar_error",
        reason: error.message,
        status: (error.statusCode ?? 400) >= 500 ? 500 : (error.statusCode ?? 400),
      });
    }

    // Non-GoogleCalendarApiError - let withApiGuards handle it
    throw error;
  }
});
