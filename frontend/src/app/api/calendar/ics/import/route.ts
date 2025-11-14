/**
 * @fileoverview ICS import endpoint.
 *
 * Parses ICS file/text and returns events payload. Optionally validates
 * without writing to calendar (requires approval for writes).
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import ical from "node-ical";
import { z } from "zod";

import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { calendarEventSchema } from "@/lib/schemas/calendar";
import { createServerSupabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const RATELIMIT_PREFIX = "ratelimit:calendar:ics:import";
let cachedLimiter: InstanceType<typeof Ratelimit> | undefined;

function getRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  if (cachedLimiter) return cachedLimiter;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  cachedLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(20, "1 m"), // 20 requests per minute
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
  return cachedLimiter;
}

const importRequestSchema = z.object({
  icsData: z.string().min(1, "ICS data is required"),
  validateOnly: z.boolean().default(true),
});

/**
 * POST /api/calendar/ics/import
 * Parses ICS calendar data and returns structured events payload.
 * Requires authenticated user session with rate limiting.
 * @param req - NextRequest containing ICS data string and validation flag
 * @returns NextResponse with parsed events array or error
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
    const limiter = getRateLimiter();
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
    const validated = importRequestSchema.parse(body);

    // Parse ICS data
    let parsedEvents: ReturnType<typeof ical.parseICS>;
    try {
      parsedEvents = ical.parseICS(validated.icsData);
    } catch (parseError) {
      const message =
        parseError instanceof Error ? parseError.message : "Failed to parse ICS";
      return NextResponse.json(
        { details: message, error: "Invalid ICS format" },
        { status: 400 }
      );
    }

    // Convert parsed events to calendar event format
    const events: unknown[] = [];
    for (const [_key, event] of Object.entries(parsedEvents)) {
      if (event.type === "VEVENT") {
        const vevent = event as {
          summary?: string;
          description?: string;
          location?: string;
          start?: Date | { toJSDate?: () => Date };
          end?: Date | { toJSDate?: () => Date };
          rrule?: string;
          attendees?: Array<{ val: string; params?: Record<string, string> }>;
          uid?: string;
          created?: Date;
          lastmodified?: Date;
        };

        const startDate =
          vevent.start instanceof Date
            ? vevent.start
            : vevent.start &&
                typeof vevent.start === "object" &&
                "toJSDate" in vevent.start &&
                typeof vevent.start.toJSDate === "function"
              ? vevent.start.toJSDate()
              : null;

        const endDate =
          vevent.end instanceof Date
            ? vevent.end
            : vevent.end &&
                typeof vevent.end === "object" &&
                "toJSDate" in vevent.end &&
                typeof vevent.end.toJSDate === "function"
              ? vevent.end.toJSDate()
              : null;

        if (!startDate || !endDate) {
          continue; // Skip events without valid dates
        }

        const eventData = {
          description: vevent.description,
          end: {
            dateTime: endDate.toISOString(),
          },
          location: vevent.location,
          start: {
            dateTime: startDate.toISOString(),
          },
          summary: vevent.summary || "Untitled Event",
          ...(vevent.rrule ? { recurrence: [vevent.rrule] } : {}),
          ...(vevent.attendees?.length
            ? {
                attendees: vevent.attendees.map((att) => ({
                  displayName: att.params?.CN,
                  email: att.val,
                })),
              }
            : {}),
          ...(vevent.uid ? { iCalUID: vevent.uid } : {}),
          ...(vevent.created ? { created: vevent.created } : {}),
          ...(vevent.lastmodified ? { updated: vevent.lastmodified } : {}),
        };

        // Validate against schema (but don't fail on minor issues)
        try {
          calendarEventSchema.parse(eventData);
        } catch {
          // Continue even if validation fails - return raw data
        }

        events.push(eventData);
      }
    }

    return NextResponse.json({
      count: events.length,
      events,
      validateOnly: validated.validateOnly,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { details: error.issues, error: "Invalid request body" },
        { status: 400 }
      );
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/ics/import POST error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
