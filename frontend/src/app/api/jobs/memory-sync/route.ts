/**
 * @fileoverview Durable job handler for memory sync operations via QStash.
 * Processes conversation memory storage and context synchronization with
 * deduplication, retry logic, and proper telemetry.
 */

import "server-only";

import { Receiver } from "@upstash/qstash";
import { NextResponse } from "next/server";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { tryReserveKey } from "@/lib/idempotency/redis";
import { memorySyncJobSchema } from "@/lib/schemas/webhooks";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * Creates a QStash receiver for webhook signature verification.
 *
 * @return QStash receiver instance or null if not configured.
 */
function getQstashReceiver(): Receiver {
  const current = getServerEnvVar("QSTASH_CURRENT_SIGNING_KEY") as string;
  const next = getServerEnvVarWithFallback(
    "QSTASH_NEXT_SIGNING_KEY",
    current
  ) as string;
  return new Receiver({ currentSigningKey: current, nextSigningKey: next });
}

/**
 * Processes queued memory sync jobs with signature verification and deduplication.
 *
 * @param req - The incoming job request.
 * @return Response indicating success or error.
 */
export async function POST(req: Request) {
  return await withTelemetrySpan(
    "jobs.memory-sync",
    { attributes: { route: "/api/jobs/memory-sync" } },
    async (span) => {
      try {
        let receiver: Receiver;
        try {
          receiver = getQstashReceiver();
        } catch (error) {
          span.recordException(error as Error);
          return NextResponse.json(
            { error: "qstash signing keys are not configured" },
            { status: 500 }
          );
        }

        const sig = req.headers.get("Upstash-Signature");
        const body = await req.clone().text();
        const url = req.url;
        const valid = sig
          ? await receiver.verify({ body, signature: sig, url })
          : false;
        if (!valid) {
          return NextResponse.json(
            { error: "invalid qstash signature" },
            { status: 401 }
          );
        }

        const json = (await req.json()) as unknown;
        const parsed = memorySyncJobSchema.safeParse(json);
        if (!parsed.success) {
          return NextResponse.json(
            { error: "invalid job payload", issues: parsed.error.flatten() },
            { status: 400 }
          );
        }
        const { idempotencyKey, payload } = parsed.data;
        span.setAttribute("idempotency.key", idempotencyKey);
        span.setAttribute("sync.type", payload.syncType);
        span.setAttribute("session.id", payload.sessionId);
        span.setAttribute("user.id", payload.userId);

        // De-duplicate at worker level to avoid double-processing on retries
        const unique = await tryReserveKey(`memory-sync:${idempotencyKey}`, 600); // 10min TTL
        if (!unique) {
          span.setAttribute("job.duplicate", true);
          return NextResponse.json({ duplicate: true, ok: true });
        }

        const result = await processMemorySync(payload);
        return NextResponse.json({ ok: true, ...result });
      } catch (error) {
        span.recordException(error as Error);
        return NextResponse.json({ error: "internal error" }, { status: 500 });
      }
    }
  );
}

/**
 * Process a memory sync job by storing conversation memories and updating context.
 *
 * @param payload - Validated memory sync payload.
 * @return Processing result with counts and status.
 */
async function processMemorySync(payload: {
  sessionId: string;
  userId: string;
  syncType: "full" | "incremental" | "conversation";
  conversationMessages?: Array<{
    content: string;
    role: "user" | "assistant" | "system";
    timestamp: string;
    metadata?: Record<string, unknown>;
  }>;
}) {
  const supabase = await createServerSupabase();

  // Verify user has access to this session
  const { data: session, error: sessionError } = await supabase
    .from("chat_sessions")
    .select("id")
    .eq("id", payload.sessionId)
    .eq("user_id", payload.userId)
    .single();

  if (sessionError || !session) {
    throw new Error(`session_not_found_or_unauthorized: ${payload.sessionId}`);
  }

  let memoriesStored = 0;
  let contextUpdated = false;

  // Process conversation messages if provided
  if (payload.conversationMessages && payload.conversationMessages.length > 0) {
    const messagesToStore = payload.conversationMessages.slice(0, 50); // Limit batch size

    // Store conversation memories
    const memoryInserts = messagesToStore.map((msg) => ({
      content: msg.content,
      memory_type: "conversation_context" as const,
      metadata: {
        role: msg.role,
        sessionId: payload.sessionId,
        timestamp: msg.timestamp,
        ...msg.metadata,
      },
      session_id: payload.sessionId,
      user_id: payload.userId,
    }));

    const { data: insertedMemories, error: insertError } = await supabase
      .from("memories")
      .insert(memoryInserts)
      .select("id");

    if (insertError) {
      throw new Error(`memory_insert_failed: ${insertError.message}`);
    }

    memoriesStored = insertedMemories?.length ?? 0;
  }

  // Update memory context summary (simplified - could be enhanced with AI)
  if (payload.syncType === "conversation" || payload.syncType === "full") {
    const { error: updateError } = await supabase
      .from("chat_sessions")
      .update({
        memory_synced_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .eq("id", payload.sessionId);

    if (updateError) {
      throw new Error(`session_update_failed: ${updateError.message}`);
    }

    contextUpdated = true;
  }

  return {
    contextUpdated,
    memoriesStored,
    sessionId: payload.sessionId,
    syncType: payload.syncType,
  };
}
