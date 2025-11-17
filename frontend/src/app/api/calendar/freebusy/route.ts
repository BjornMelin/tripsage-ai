/**
 * @fileoverview Free/busy query endpoint.
 *
 * Queries Google Calendar free/busy information for specified calendars.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { queryFreeBusy } from "@/lib/calendar/google";
import { parseJsonBody, validateSchema } from "@/lib/next/route-helpers";
import { freeBusyRequestSchema } from "@/lib/schemas/calendar";

/**
 * POST /api/calendar/freebusy
 *
 * Query free/busy information for calendars.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with free/busy data
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "calendar:freebusy",
  telemetry: "calendar.freebusy",
})(async (req: NextRequest) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(freeBusyRequestSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const result = await queryFreeBusy(validation.data);

  return NextResponse.json(result);
});
