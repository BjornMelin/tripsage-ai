/**
 * @fileoverview Accommodation agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { z } from "zod";
import { runAccommodationAgent } from "@/lib/agents/accommodation-agent";
import { getTrustedRateLimitIdentifier } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { createServerSupabase } from "@/lib/supabase/server";
import type { AccommodationSearchRequest } from "@/schemas/agents";
import { agentSchemas } from "@/schemas/agents";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const RequestSchema = agentSchemas.accommodationSearchRequestSchema;

/**
 * POST /api/agents/accommodations
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();
    const user = (await supabase.auth.getUser()).data.user;

    const raw = (await req.json().catch(() => ({}))) as unknown;
    let body: AccommodationSearchRequest;
    try {
      body = RequestSchema.parse(raw);
    } catch (err) {
      const zerr = err as z.ZodError;
      return NextResponse.json(
        { error: "invalid_request", issues: zerr.issues },
        { status: 400 }
      );
    }

    const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
    const { model } = await resolveProvider(user?.id ?? "anon", modelHint);
    const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);

    const result = runAccommodationAgent({ identifier, model }, body);
    return result.toUIMessageStreamResponse();
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/agents/accommodations:fatal", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
