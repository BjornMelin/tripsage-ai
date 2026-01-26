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
import {
  getMany,
  getMaybeSingle,
  getSingle,
  insertMany,
  insertSingle,
  updateSingle,
} from "@/lib/supabase/typed-helpers";

/**
 * Normalizes content for deduplication by extracting text from structured content.
 * Handles both JSONB content from DB and structured { text: string } objects.
 * @param content - Content to normalize (object with text property or primitive)
 * @returns Normalized string for dedupe key generation
 */
function normalizeContentForDedupe(content: unknown): string {
  if (typeof content === "object" && content && "text" in content) {
    const text = (content as { text?: unknown }).text;
    if (typeof text === "string") return text;
    if (typeof text === "number" || typeof text === "boolean") return String(text);
    return JSON.stringify(text ?? "");
  }
  return JSON.stringify(content ?? "");
}

function normalizeMetadataForDedupe(value: unknown): string {
  return JSON.stringify(value ?? null);
}

function buildTurnDedupeKey(params: {
  createdAt: string;
  role: string;
  content: unknown;
  attachments: unknown;
  toolCalls: unknown;
  toolResults: unknown;
}): string {
  const content = normalizeContentForDedupe(params.content);
  const attachments = normalizeMetadataForDedupe(params.attachments);
  const toolCalls = normalizeMetadataForDedupe(params.toolCalls);
  const toolResults = normalizeMetadataForDedupe(params.toolResults);
  return `${params.createdAt}|${params.role}|${content}|${attachments}|${toolCalls}|${toolResults}`;
}

function normalizeMessageTimestamp(timestamp: unknown, nowIso: () => string): string {
  if (typeof timestamp !== "string") return nowIso();
  const trimmed = timestamp.trim();
  if (trimmed.length === 0) return nowIso();
  const parsed = Date.parse(trimmed);
  if (Number.isNaN(parsed)) return nowIso();
  return trimmed;
}

/**
 * Dependencies for the memory sync job handler.
 */
export interface MemorySyncJobDeps {
  /** Admin Supabase client for database operations. */
  supabase: TypedAdminSupabase;
  /** Optional clock for deterministic timestamps during tests. */
  clock?: { now: () => string };
}

type ChatSessionUpdatePayload =
  Database["public"]["Tables"]["chat_sessions"]["Update"] & {
    memory_synced_at?: string | null;
  };

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
  // Process conversation messages in bounded batches to reduce payload size and avoid timeouts.
  const MaxConversationBatchSize = 50;

  // Verify user has access to this session
  const { data: session, error: sessionError } = await getSingle(
    supabase,
    "chat_sessions",
    (qb) => qb.eq("id", payload.sessionId).eq("user_id", payload.userId),
    { select: "id", validate: false }
  );

  if (sessionError || !session) {
    throw new MemorySyncAccessError("Session not found or user unauthorized", {
      sessionId: payload.sessionId,
      userId: payload.userId,
    });
  }

  let memoriesStored = 0;
  let contextUpdated = false;

  // Process conversation messages if provided
  const conversationMessages = payload.conversationMessages ?? [];
  if (conversationMessages.length > 0) {
    // Supabase PostgREST clients do not support multi-statement transactions in this context.
    // We rely on idempotency + retries to reach eventual consistency: partial batch inserts
    // are safe because dedupe prevents duplicates, and reruns can repair missed turns or
    // session updates after transient failures/timeouts.
    const messageBatches = [];
    for (let i = 0; i < conversationMessages.length; i += MaxConversationBatchSize) {
      messageBatches.push(conversationMessages.slice(i, i + MaxConversationBatchSize));
    }

    // Ensure memory session exists
    const { data: memorySession, error: sessionCheckError } = await getMaybeSingle(
      supabase,
      "sessions",
      (qb) => qb.eq("id", payload.sessionId).eq("user_id", payload.userId),
      { schema: "memories", select: "id", validate: false }
    );

    if (sessionCheckError) {
      throw new MemorySyncDatabaseError("Memory session check failed", {
        cause: sessionCheckError,
        operation: "session_check",
        sessionId: payload.sessionId,
      });
    }

    // Create session if it doesn't exist
    if (!memorySession) {
      const firstMessageContent = conversationMessages[0]?.content?.trim() ?? "";
      const title =
        firstMessageContent.length > 0
          ? firstMessageContent.substring(0, 100)
          : "Untitled session";
      const { error: createError } = await insertSingle(
        supabase,
        "sessions",
        {
          id: payload.sessionId,
          metadata: {},
          title,
          // biome-ignore lint/style/useNamingConvention: Database field name
          user_id: payload.userId,
        },
        { schema: "memories" }
      );

      if (createError) {
        throw new MemorySyncDatabaseError("Memory session creation failed", {
          cause: createError,
          operation: "session_create",
          sessionId: payload.sessionId,
        });
      }
    }

    // Store conversation turns with best-effort dedupe for retries.
    let storedTurns = 0;
    for (const messagesToStore of messageBatches) {
      if (messagesToStore.length === 0) continue;
      const normalizedTimestamps = messagesToStore.map((msg) =>
        normalizeMessageTimestamp(msg.timestamp, nowIso)
      );
      const turnInserts: Database["memories"]["Tables"]["turns"]["Insert"][] =
        messagesToStore.map((msg, index) => ({
          attachments: jsonSchema.parse(msg.metadata?.attachments ?? []),
          // Convert string content to JSONB format: { text: string }
          content: {
            text: msg.content,
          },
          // biome-ignore lint/style/useNamingConvention: Database field name
          created_at: normalizedTimestamps[index],
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

      const turnTimestamps = normalizedTimestamps;
      // Indexed by memories_turns_session_idx (session_id, created_at).
      const { data: existingTurns, error: existingError } = await getMany(
        supabase,
        "turns",
        (qb) => qb.eq("session_id", payload.sessionId).in("created_at", turnTimestamps),
        {
          schema: "memories",
          select: "created_at, role, content, attachments, tool_calls, tool_results",
          validate: false,
        }
      );

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
          return buildTurnDedupeKey({
            attachments: turn.attachments,
            content: turn.content,
            createdAt: turn.created_at,
            role: turn.role,
            toolCalls: turn.tool_calls,
            toolResults: turn.tool_results,
          });
        })
      );
      const dedupedInserts = turnInserts.filter((turn) => {
        return !existingKeys.has(
          buildTurnDedupeKey({
            attachments: turn.attachments,
            content: turn.content,
            createdAt: turn.created_at ?? "",
            role: turn.role ?? "",
            toolCalls: turn.tool_calls,
            toolResults: turn.tool_results,
          })
        );
      });

      if (dedupedInserts.length > 0) {
        const { error: insertError } = await insertMany(
          supabase,
          "turns",
          dedupedInserts,
          { schema: "memories" }
        );

        if (insertError) {
          throw new MemorySyncDatabaseError("Memory turn insert failed", {
            cause: insertError,
            context: { turnCount: dedupedInserts.length },
            operation: "turn_insert",
            sessionId: payload.sessionId,
          });
        }
      }

      storedTurns += dedupedInserts.length;
    }

    // Update session last_synced_at
    const { error: syncError } = await updateSingle(
      supabase,
      "sessions",
      {
        // biome-ignore lint/style/useNamingConvention: Database field name
        last_synced_at: nowIso(),
      },
      (qb) => qb.eq("id", payload.sessionId),
      { schema: "memories" }
    );
    if (syncError) {
      throw new MemorySyncDatabaseError("Memory session sync update failed", {
        cause: syncError,
        operation: "session_sync_update",
        sessionId: payload.sessionId,
      });
    }

    memoriesStored = storedTurns;
  }

  // Update memory context summary (simplified - could be enhanced with AI)
  {
    const updatePayload: ChatSessionUpdatePayload = {
      // biome-ignore lint/style/useNamingConvention: Database field name
      memory_synced_at: nowIso(),
      // biome-ignore lint/style/useNamingConvention: Database field name
      updated_at: nowIso(),
    };

    const { error: updateError } = await updateSingle(
      supabase,
      "chat_sessions",
      updatePayload,
      (qb) => qb.eq("id", payload.sessionId),
      { validate: false }
    );

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
