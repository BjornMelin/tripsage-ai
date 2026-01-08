/**
 * @fileoverview Pure handler for memory sync jobs.
 */

import "server-only";

import { MemorySyncAccessError, MemorySyncDatabaseError } from "@domain/memory/errors";
import { jsonSchema } from "@schemas/supabase";
import type { MemorySyncJob } from "@schemas/webhooks";
import { nowIso as secureNowIso } from "@/lib/security/random";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";

/**
 * Dependencies for the memory sync job handler.
 */
export interface MemorySyncJobDeps {
  /** Admin Supabase client for database operations. */
  supabase: TypedAdminSupabase;
  /** Optional clock for deterministic timestamps during tests. */
  clock?: { now: () => string };
}

/**
 * Handles memory sync jobs by validating session access, storing conversation turns,
 * and updating sync timestamps.
 *
 * @param deps - Dependencies (Supabase client, optional clock)
 * @param payload - Memory sync job payload with session and user metadata
 * @returns Sync result with counts and metadata
 * @throws {MemorySyncAccessError} When session is not found or user is unauthorized
 * @throws {MemorySyncDatabaseError} When database operations fail
 */
export async function handleMemorySyncJob(
  deps: MemorySyncJobDeps,
  payload: MemorySyncJob["payload"]
): Promise<{
  contextUpdated: boolean;
  memoriesStored: number;
  sessionId: string;
  syncType: MemorySyncJob["payload"]["syncType"];
}> {
  const { supabase } = deps;
  const nowIso = deps.clock?.now ?? (() => secureNowIso());
  // Limit each sync batch to 50 messages to reduce payload size and avoid timeouts.
  const MaxConversationBatchSize = 50;

  // Verify user has access to this session
  const { data: session, error: sessionError } = await supabase
    .from("chat_sessions")
    .select("id")
    .eq("id", payload.sessionId)
    .eq("user_id", payload.userId)
    .single();

  if (sessionError || !session) {
    throw new MemorySyncAccessError("Session not found or user unauthorized", {
      sessionId: payload.sessionId,
      userId: payload.userId,
    });
  }

  let memoriesStored = 0;
  let contextUpdated = false;

  // Process conversation messages if provided
  if (payload.conversationMessages && payload.conversationMessages.length > 0) {
    // Supabase transactions are not available here; rely on idempotency + retries.
    const messagesToStore = payload.conversationMessages.slice(
      0,
      MaxConversationBatchSize
    );

    // Ensure memory session exists
    const { data: memorySession, error: sessionCheckError } = await supabase
      .schema("memories")
      .from("sessions")
      .select("id")
      .eq("id", payload.sessionId)
      .eq("user_id", payload.userId)
      .single();

    if (sessionCheckError && sessionCheckError.code !== "PGRST116") {
      throw new MemorySyncDatabaseError("Memory session check failed", {
        cause: sessionCheckError,
        operation: "session_check",
        sessionId: payload.sessionId,
      });
    }

    // Create session if it doesn't exist
    if (!memorySession) {
      const firstMessageContent = messagesToStore[0]?.content?.trim() ?? "";
      const title =
        firstMessageContent.length > 0
          ? firstMessageContent.substring(0, 100)
          : "Untitled session";
      const { error: createError } = await supabase
        .schema("memories")
        .from("sessions")
        .insert({
          id: payload.sessionId,
          metadata: {},
          title,
          // biome-ignore lint/style/useNamingConvention: Database field name
          user_id: payload.userId,
        });

      if (createError) {
        throw new MemorySyncDatabaseError("Memory session creation failed", {
          cause: createError,
          operation: "session_create",
          sessionId: payload.sessionId,
        });
      }
    }

    // Store conversation turns with best-effort dedupe for retries.
    const turnInserts: Database["memories"]["Tables"]["turns"]["Insert"][] =
      messagesToStore.map((msg) => ({
        attachments: jsonSchema.parse(msg.metadata?.attachments ?? []),
        // Convert string content to JSONB format: { text: string }
        content: {
          text: msg.content,
        },
        // biome-ignore lint/style/useNamingConvention: Database field name
        created_at: msg.timestamp,
        // biome-ignore lint/style/useNamingConvention: Database field name
        pii_scrubbed: false, // PII scrubbing handled upstream (chat ingestion).
        role: msg.role,
        // biome-ignore lint/style/useNamingConvention: Database field name
        session_id: payload.sessionId,
        // biome-ignore lint/style/useNamingConvention: Database field name
        tool_calls: jsonSchema.parse(msg.metadata?.toolCalls ?? []),
        // biome-ignore lint/style/useNamingConvention: Database field name
        tool_results: jsonSchema.parse(msg.metadata?.toolResults ?? []),
        // biome-ignore lint/style/useNamingConvention: Database field name
        user_id: payload.userId,
      }));

    const turnTimestamps = messagesToStore.map((msg) => msg.timestamp);
    const { data: existingTurns, error: existingError } = await supabase
      .schema("memories")
      .from("turns")
      .select("created_at, role, content")
      .eq("session_id", payload.sessionId)
      .in("created_at", turnTimestamps);

    if (existingError) {
      throw new MemorySyncDatabaseError("Memory turn dedupe lookup failed", {
        cause: existingError,
        context: { turnCount: turnInserts.length },
        operation: "turn_dedupe_lookup",
        sessionId: payload.sessionId,
      });
    }

    const existingKeys = new Set(
      (existingTurns ?? []).map((turn) => {
        const content =
          typeof turn.content === "object" && turn.content && "text" in turn.content
            ? String(turn.content.text ?? "")
            : JSON.stringify(turn.content ?? "");
        return `${turn.created_at}|${turn.role}|${content}`;
      })
    );
    const dedupedInserts = turnInserts.filter((turn) => {
      const content =
        typeof turn.content === "object" && turn.content && "text" in turn.content
          ? String(turn.content.text ?? "")
          : JSON.stringify(turn.content ?? "");
      return !existingKeys.has(`${turn.created_at}|${turn.role}|${content}`);
    });

    if (dedupedInserts.length > 0) {
      const { error: insertError } = await supabase
        .schema("memories")
        .from("turns")
        .insert(dedupedInserts);

      if (insertError) {
        throw new MemorySyncDatabaseError("Memory turn insert failed", {
          cause: insertError,
          context: { turnCount: dedupedInserts.length },
          operation: "turn_insert",
          sessionId: payload.sessionId,
        });
      }
    }

    // Update session last_synced_at
    const { error: syncError } = await supabase
      .schema("memories")
      .from("sessions")
      .update({
        // biome-ignore lint/style/useNamingConvention: Database field name
        last_synced_at: nowIso(),
      })
      .eq("id", payload.sessionId);
    if (syncError) {
      throw new MemorySyncDatabaseError("Memory session sync update failed", {
        cause: syncError,
        operation: "session_sync_update",
        sessionId: payload.sessionId,
      });
    }

    memoriesStored = messagesToStore.length;
  }

  // Update memory context summary (simplified - could be enhanced with AI)
  {
    const { error: updateError } = await supabase
      .from("chat_sessions")
      .update({
        // biome-ignore lint/style/useNamingConvention: Database field name
        memory_synced_at: nowIso(),
        // biome-ignore lint/style/useNamingConvention: Database field name
        updated_at: nowIso(),
      })
      .eq("id", payload.sessionId);

    if (updateError) {
      throw new MemorySyncDatabaseError("Chat session update failed", {
        cause: updateError,
        operation: "chat_session_update",
        sessionId: payload.sessionId,
      });
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
