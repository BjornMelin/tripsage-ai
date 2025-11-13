/**
 * @fileoverview Calendar connection status endpoint.
 *
 * Returns connection status, granted scopes, and list of calendars for the
 * authenticated user.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { hasGoogleCalendarScopes } from "@/lib/calendar/auth";
import { listCalendars } from "@/lib/calendar/google";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { createServerSupabase } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

const RATELIMIT_PREFIX = "ratelimit:calendar:status";
let cachedLimiter: InstanceType<typeof Ratelimit> | undefined;

function getRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  if (cachedLimiter) return cachedLimiter;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  cachedLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(60, "1 m"), // 60 requests per minute
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
  return cachedLimiter;
}

/**
 * GET /api/calendar/status
 *
 * Get calendar connection status and list of calendars.
 */
export async function GET(_req: NextRequest) {
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
      const identifier = user.id;
      const { success, remaining, reset } = await limiter.limit(identifier);
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
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/status GET error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
