/**
 * @fileoverview Router agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Classifies user messages into agent workflows
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { classifyUserMessage } from "@/lib/agents/router-agent";
import { resolveProvider } from "@/lib/providers/registry";
import { createServerSupabase } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/**
 * POST /api/agents/router
 *
 * Classifies user message into an agent workflow.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();
    const user = (await supabase.auth.getUser()).data.user;

    const raw = (await req.json().catch(() => ({}))) as unknown;
    const body = raw as { message?: string };
    if (!body.message || typeof body.message !== "string") {
      return NextResponse.json(
        { error: "invalid_request", message: "message field required" },
        { status: 400 }
      );
    }

    const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
    const { model } = await resolveProvider(user?.id ?? "anon", modelHint);

    const classification = await classifyUserMessage({ model }, body.message);
    return NextResponse.json(classification);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/agents/router:fatal", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
