/**
 * @fileoverview ICS export endpoint.
 *
 * Generates ICS file from events payload. Supports caching for performance.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import ical from "ical-generator";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { RecurringDateGenerator } from "@/lib/dates/recurring-rules";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { calendarEventSchema } from "@/lib/schemas/calendar";
import { createServerSupabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const RATELIMIT_PREFIX = "ratelimit:calendar:ics:export";
let cachedLimiter: InstanceType<typeof Ratelimit> | undefined;

function getRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  if (cachedLimiter) return cachedLimiter;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  cachedLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(30, "1 m"), // 30 requests per minute
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
  return cachedLimiter;
}

const exportRequestSchema = z.object({
  calendarName: z.string().default("TripSage Calendar"),
  events: z.array(calendarEventSchema).min(1, "At least one event is required"),
  timezone: z.string().optional(),
});

/**
 * Handles the ICS export request by validating payloads, enforcing rate
 * limits, and returning the generated calendar file.
 *
 * @param req - HTTP request containing calendar metadata and Google-style events.
 * @returns Response with the ICS attachment or JSON error payload.
 */
export async function POST(req: NextRequest): Promise<NextResponse> {
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
    const validated = exportRequestSchema.parse(body);

    // Create calendar
    const calendar = ical({
      name: validated.calendarName,
      timezone: validated.timezone || "UTC",
    });

    // Add events
    for (const event of validated.events) {
      const startDate =
        event.start.dateTime instanceof Date
          ? event.start.dateTime
          : event.start.date
            ? DateUtils.parse(event.start.date)
            : new Date();

      const endDate =
        event.end.dateTime instanceof Date
          ? event.end.dateTime
          : event.end.date
            ? DateUtils.parse(event.end.date)
            : DateUtils.add(startDate, 1, "hours"); // Default 1 hour

      const eventData = {
        description: event.description,
        end: endDate,
        location: event.location,
        start: startDate,
        summary: event.summary,
        ...(event.recurrence?.length
          ? {
              recurrence: [
                RecurringDateGenerator.toRRule(
                  RecurringDateGenerator.parseRRule(event.recurrence[0])
                ),
              ],
            }
          : {}),
        ...(event.iCalUID ? { uid: event.iCalUID } : {}),
        ...(event.created ? { created: event.created } : {}),
        ...(event.updated ? { lastModified: event.updated } : {}),
      };

      const ev = calendar.createEvent(eventData);

      if (event.attendees?.length) {
        for (const att of event.attendees) {
          ev.createAttendee({
            email: att.email,
            name: att.displayName,
            rsvp: !att.optional,
            // biome-ignore lint/suspicious/noExplicitAny: third-party type casting for ical types
            status: eventAttendeeStatusToIcal(att.responseStatus) as unknown as any,
          });
        }
      }

      if (event.reminders?.overrides?.length) {
        for (const rem of event.reminders.overrides) {
          ev.createAlarm({
            trigger: rem.minutes * 60, // seconds
            // biome-ignore lint/suspicious/noExplicitAny: third-party type casting for ical types
            type: reminderMethodToIcal(rem.method) as unknown as any,
          });
        }
      }
    }

    // Generate ICS string
    const icsString = calendar.toString();

    return new NextResponse(icsString, {
      headers: {
        "Content-Disposition": `attachment; filename="${validated.calendarName.replace(/[^a-z0-9]/gi, "_")}.ics"`,
        "Content-Type": "text/calendar; charset=utf-8",
      },
      status: 200,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { details: error.issues, error: "Invalid request body" },
        { status: 400 }
      );
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/ics/export POST error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

/**
 * Converts an attendee response status to the canonical iCal constant.
 *
 * @param status - Google Calendar style attendee status.
 * @returns iCal attendee status string.
 */
function eventAttendeeStatusToIcal(
  status: string
): "ACCEPTED" | "DECLINED" | "TENTATIVE" | "NEEDS-ACTION" {
  switch (status) {
    case "accepted":
      return "ACCEPTED";
    case "declined":
      return "DECLINED";
    case "tentative":
      return "TENTATIVE";
    default:
      return "NEEDS-ACTION";
  }
}

/**
 * Normalizes reminder methods to the subset supported by iCal alarms.
 *
 * @param method - Notification channel provided by Google events.
 * @returns Alarm type accepted by ical-generator.
 */
function reminderMethodToIcal(method: string): "display" | "email" | "audio" {
  switch (method) {
    case "email":
      return "email";
    default:
      return "display";
  }
}
