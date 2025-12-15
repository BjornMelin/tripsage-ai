/**
 * @fileoverview Durable job handler for memory sync operations via QStash.
 * Processes conversation memory storage and context synchronization with
 * deduplication, retry logic, and proper telemetry.
 */

import "server-only";

import { memorySyncJobSchema } from "@schemas/webhooks";
import { NextResponse } from "next/server";
import { errorResponse, validateSchema } from "@/lib/api/route-helpers";
import { tryReserveKey } from "@/lib/idempotency/redis";
import { getQstashReceiver, verifyQstashRequest } from "@/lib/qstash/receiver";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import { withTelemetrySpan } from "@/lib/telemetry/span";

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
        let receiver: ReturnType<typeof getQstashReceiver>;
        try {
          receiver = getQstashReceiver();
        } catch (error) {
          span.recordException(error as Error);
          return errorResponse({
            err: error,
            error: "configuration_error",
            reason: "QStash signing keys are misconfigured",
            status: 500,
          });
        }

        const verified = await verifyQstashRequest(req, receiver);
        if (!verified.ok) {
          span.addEvent("unauthorized_attempt", {
            hasSignature: verified.reason !== "missing_signature",
            reason: verified.reason,
            url: req.url,
          });
          return verified.response;
        }

        let json: unknown;
        try {
          json = JSON.parse(verified.body) as unknown;
        } catch (error) {
          return errorResponse({
            err: error,
            error: "invalid_request",
            reason: "Malformed JSON in request body",
            status: 400,
          });
        }

        const validation = validateSchema(memorySyncJobSchema, json);
        if ("error" in validation) {
          return validation.error;
        }
        const { idempotencyKey, payload } = validation.data;
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
        return errorResponse({
          err: error,
          error: "internal",
          reason: "Memory sync job failed",
          status: 500,
        });
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
  const supabase = createAdminSupabase();

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

    // Ensure memory session exists
    const { data: memorySession, error: sessionCheckError } = await supabase
      .schema("memories")
      .from("sessions")
      .select("id")
      .eq("id", payload.sessionId)
      .eq("user_id", payload.userId)
      .single();

    if (sessionCheckError && sessionCheckError.code !== "PGRST116") {
      throw new Error(`memory_session_check_failed: ${sessionCheckError.message}`);
    }

    // Create session if it doesn't exist
    if (!memorySession) {
      const { error: createError } = await supabase
        .schema("memories")
        .from("sessions")
        .insert({
          id: payload.sessionId,
          metadata: {},
          title: messagesToStore[0]?.content?.substring(0, 100) || "Untitled session",
          user_id: payload.userId,
        });

      if (createError) {
        throw new Error(`memory_session_create_failed: ${createError.message}`);
      }
    }

    // Store conversation turns
    const turnInserts: Database["memories"]["Tables"]["turns"]["Insert"][] =
      messagesToStore.map((msg) => ({
        attachments: ((msg.metadata?.attachments as unknown[]) ||
          []) as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["attachments"],
        // Convert string content to JSONB format: { text: string }
        content: {
          text: msg.content,
        } as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["content"],
        pii_scrubbed: false,
        role: msg.role,
        session_id: payload.sessionId,
        tool_calls: ((msg.metadata?.toolCalls as unknown[]) ||
          []) as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["tool_calls"],
        tool_results: ((msg.metadata?.toolResults as unknown[]) ||
          []) as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["tool_results"],
        user_id: payload.userId,
      }));

    const { error: insertError } = await supabase
      .schema("memories")
      .from("turns")
      .insert(turnInserts)
      .select("id");

    if (insertError) {
      throw new Error(`memory_turn_insert_failed: ${insertError.message}`);
    }

    // Update session last_synced_at
    await supabase
      .schema("memories")
      .from("sessions")
      .update({ last_synced_at: new Date().toISOString() })
      .eq("id", payload.sessionId);

    memoriesStored = messagesToStore.length;
  }

  // Update memory context summary (simplified - could be enhanced with AI)
  if (
    payload.syncType === "conversation" ||
    payload.syncType === "full" ||
    payload.syncType === "incremental"
  ) {
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
