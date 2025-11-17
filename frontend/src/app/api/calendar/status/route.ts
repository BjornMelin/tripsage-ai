/**
 * @fileoverview Calendar connection status endpoint.
 *
 * Returns connection status, granted scopes, and list of calendars for the
 * authenticated user.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { hasGoogleCalendarScopes } from "@/lib/calendar/auth";
import { listCalendars } from "@/lib/calendar/google";

export const dynamic = "force-dynamic";

/**
 * GET /api/calendar/status
 *
 * Get calendar connection status and list of calendars.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with calendar status and list
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "calendar:status",
  telemetry: "calendar.status",
})(async (_req: NextRequest) => {
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
    if (error instanceof Error && error.message.includes("token")) {
      return NextResponse.json(
        {
          connected: false,
          message: "Google Calendar token expired. Please reconnect your account.",
        },
        { status: 200 }
      );
    }
    throw error;
  }
});
