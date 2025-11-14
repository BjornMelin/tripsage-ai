/**
 * @fileoverview Calendar events CRUD endpoint.
 *
 * Handles GET (list), POST (create), PATCH (update), and DELETE operations
 * for calendar events.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import {
  createEvent,
  deleteEvent,
  listEvents,
  updateEvent,
} from "@/lib/calendar/google";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import {
  createEventRequestSchema,
  eventsListRequestSchema,
  updateEventRequestSchema,
} from "@/lib/schemas/calendar";
import { createServerSupabase } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

const RATELIMIT_PREFIX_READ = "ratelimit:calendar:events:read";
const RATELIMIT_PREFIX_WRITE = "ratelimit:calendar:events:write";
let cachedReadLimiter: InstanceType<typeof Ratelimit> | undefined;
let cachedWriteLimiter: InstanceType<typeof Ratelimit> | undefined;

function getReadRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  if (cachedReadLimiter) return cachedReadLimiter;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  cachedReadLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(60, "1 m"), // 60 requests per minute
    prefix: RATELIMIT_PREFIX_READ,
    redis: Redis.fromEnv(),
  });
  return cachedReadLimiter;
}

function getWriteRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  if (cachedWriteLimiter) return cachedWriteLimiter;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  cachedWriteLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(10, "1 m"), // 10 requests per minute
    prefix: RATELIMIT_PREFIX_WRITE,
    redis: Redis.fromEnv(),
  });
  return cachedWriteLimiter;
}

/**
 * GET /api/calendar/events
 *
 * List events from a calendar.
 */
export async function GET(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Rate limit
    const limiter = getReadRateLimiter();
    if (limiter) {
      const { success, remaining, reset } = await limiter.limit(user.id);
      if (!success) {
        return NextResponse.json(
          { error: "Rate limit exceeded" },
          {
            headers: {
              "X-RateLimit-Remaining": String(remaining),
              "X-RateLimit-Reset": String(reset),
            },
            status: 429,
          }
        );
      }
    }

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

    const validated = eventsListRequestSchema.parse(params);
    const result = await listEvents(validated);

    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      // Zod validation error
      return NextResponse.json(
        { details: error, error: "Invalid request parameters" },
        { status: 400 }
      );
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/events GET error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

/**
 * POST /api/calendar/events
 *
 * Create a new calendar event.
 */
export async function POST(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Rate limit
    const limiter = getWriteRateLimiter();
    if (limiter) {
      const { success, remaining, reset } = await limiter.limit(user.id);
      if (!success) {
        return NextResponse.json(
          { error: "Rate limit exceeded" },
          {
            headers: {
              "X-RateLimit-Remaining": String(remaining),
              "X-RateLimit-Reset": String(reset),
            },
            status: 429,
          }
        );
      }
    }

    const body = await req.json();
    const calendarId = (body.calendarId as string) || "primary";

    // Convert date strings to Date objects if needed
    if (body.start?.dateTime && typeof body.start.dateTime === "string") {
      body.start.dateTime = new Date(body.start.dateTime);
    }
    if (body.start?.date && typeof body.start.date === "string") {
      // Keep as string for all-day events
    }
    if (body.end?.dateTime && typeof body.end.dateTime === "string") {
      body.end.dateTime = new Date(body.end.dateTime);
    }
    if (body.end?.date && typeof body.end.date === "string") {
      // Keep as string for all-day events
    }

    const validated = createEventRequestSchema.parse(body);
    const result = await createEvent(validated, calendarId);

    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      return NextResponse.json(
        { details: error, error: "Invalid request body" },
        { status: 400 }
      );
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/events POST error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

/**
 * PATCH /api/calendar/events?eventId=...&calendarId=...
 *
 * Update an existing calendar event.
 */
export async function PATCH(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Rate limit
    const limiter = getWriteRateLimiter();
    if (limiter) {
      const { success, remaining, reset } = await limiter.limit(user.id);
      if (!success) {
        return NextResponse.json(
          { error: "Rate limit exceeded" },
          {
            headers: {
              "X-RateLimit-Remaining": String(remaining),
              "X-RateLimit-Reset": String(reset),
            },
            status: 429,
          }
        );
      }
    }

    const { searchParams } = new URL(req.url);
    const eventId = searchParams.get("eventId");
    const calendarId = searchParams.get("calendarId") || "primary";

    if (!eventId) {
      return NextResponse.json(
        { error: "eventId query parameter is required" },
        { status: 400 }
      );
    }

    const body = await req.json();

    // Convert date strings to Date objects if needed
    if (body.start?.dateTime && typeof body.start.dateTime === "string") {
      body.start.dateTime = new Date(body.start.dateTime);
    }
    if (body.end?.dateTime && typeof body.end.dateTime === "string") {
      body.end.dateTime = new Date(body.end.dateTime);
    }

    const validated = updateEventRequestSchema.parse(body);
    const result = await updateEvent(eventId, validated, calendarId);

    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      return NextResponse.json(
        { details: error, error: "Invalid request body" },
        { status: 400 }
      );
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/events PATCH error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

/**
 * DELETE /api/calendar/events?eventId=...&calendarId=...
 *
 * Delete a calendar event.
 */
export async function DELETE(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Rate limit
    const limiter = getWriteRateLimiter();
    if (limiter) {
      const { success, remaining, reset } = await limiter.limit(user.id);
      if (!success) {
        return NextResponse.json(
          { error: "Rate limit exceeded" },
          {
            headers: {
              "X-RateLimit-Remaining": String(remaining),
              "X-RateLimit-Reset": String(reset),
            },
            status: 429,
          }
        );
      }
    }

    const { searchParams } = new URL(req.url);
    const eventId = searchParams.get("eventId");
    const calendarId = searchParams.get("calendarId") || "primary";

    if (!eventId) {
      return NextResponse.json(
        { error: "eventId query parameter is required" },
        { status: 400 }
      );
    }

    await deleteEvent(eventId, calendarId);

    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/events DELETE error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
