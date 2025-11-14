/**
 * @fileoverview Free/busy query endpoint.
 *
 * Queries Google Calendar free/busy information for specified calendars.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { queryFreeBusy } from "@/lib/calendar/google";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { freeBusyRequestSchema } from "@/lib/schemas/calendar";
import { createServerSupabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const RATELIMIT_PREFIX = "ratelimit:calendar:freebusy";
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

/**
 * POST /api/calendar/freebusy
 *
 * Query free/busy information for calendars.
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
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      return NextResponse.json(
        { details: error, error: "Invalid request body" },
        { status: 400 }
      );
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("/api/calendar/freebusy POST error:", { message });
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
