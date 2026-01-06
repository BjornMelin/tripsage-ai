/**
 * @fileoverview Free/busy query endpoint.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import { freeBusyRequestSchema } from "@schemas/calendar";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, validateSchema } from "@/lib/api/route-helpers";
import { queryFreeBusy } from "@/lib/calendar/google";

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
  if (!parsed.ok) return parsed.error;

  const validation = validateSchema(freeBusyRequestSchema, parsed.data);
  if (!validation.ok) return validation.error;
  const result = await queryFreeBusy(validation.data);

  return NextResponse.json(result);
});
