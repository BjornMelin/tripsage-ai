/**
 * @fileoverview Free/busy query endpoint.
 *
 * Queries Google Calendar free/busy information for specified calendars.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { queryFreeBusy } from "@/lib/calendar/google";
import { freeBusyRequestSchema } from "@/lib/schemas/calendar";

export const dynamic = "force-dynamic";

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
  const body = await req.json();

  // Convert date strings to Date objects
  if (body.timeMin && typeof body.timeMin === "string") {
    body.timeMin = new Date(body.timeMin);
  }
  if (body.timeMax && typeof body.timeMax === "string") {
    body.timeMax = new Date(body.timeMax);
  }

  const validated = freeBusyRequestSchema.parse(body);
  const result = await queryFreeBusy(validated);

  return NextResponse.json(result);
});
