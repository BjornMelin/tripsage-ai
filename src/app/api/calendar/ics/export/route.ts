/**
 * @fileoverview ICS export endpoint.
 *
 * Generates ICS file from events payload using shared generator.
 * Authentication required.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import { type IcsExportRequest, icsExportRequestSchema } from "@schemas/calendar";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { generateIcsFromEvents, sanitizeCalendarFilename } from "@/lib/calendar/ics";

/**
 * Handles the ICS export request by validating payloads, enforcing rate
 * limits, and returning the generated calendar file.
 *
 * Uses the shared ICS generator to ensure consistency with AI tools.
 *
 * @param req - HTTP request containing calendar metadata and Google-style events.
 * @param routeContext - Route context from withApiGuards
 * @returns Response with the ICS attachment or JSON error payload.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "calendar:ics:export",
  schema: icsExportRequestSchema,
  telemetry: "calendar.ics.export",
})((_req: NextRequest, _context, validated: IcsExportRequest): NextResponse => {
  const { icsString } = generateIcsFromEvents({
    calendarName: validated.calendarName,
    events: validated.events,
    timezone: validated.timezone,
  });

  const filename = sanitizeCalendarFilename(validated.calendarName);

  return new NextResponse(icsString, {
    headers: {
      "Content-Disposition": `attachment; filename="${filename}.ics"`,
      "Content-Type": "text/calendar; charset=utf-8",
    },
    status: 200,
  });
});
