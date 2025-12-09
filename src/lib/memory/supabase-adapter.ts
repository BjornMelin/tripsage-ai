/**
 * @fileoverview Supabase memory adapter implementation.
 *
 * Uses the canonical `memories.*` schema (memories.sessions, memories.turns, memories.turn_embeddings)
 * as the long-term store for conversation context. This adapter handles reads and writes
 * for the orchestrator and is considered authoritative for recall and analytics.
 */

import "server-only";

import type { MemoryContextResponse } from "@schemas/chat";
import type { SupabaseClient } from "@supabase/supabase-js";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryIntent,
} from "./orchestrator";

type AdminClient = SupabaseClient<Database>;
type MemoryTurnRow = Database["memories"]["Tables"]["turns"]["Row"];

const MAX_CONTEXT_ITEMS = 10;

async function handleFetchContext(
  supabase: AdminClient,
  intent: Extract<MemoryIntent, { type: "fetchContext" }>
): Promise<MemoryAdapterExecutionResult> {
  const limit = intent.limit && intent.limit > 0 ? intent.limit : MAX_CONTEXT_ITEMS;

  // Fetch recent turns for this user (and session when available).
  let query = supabase
    .schema("memories")
    .from("turns")
    .select("id, content, created_at, session_id")
    .eq("user_id", intent.userId)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (intent.sessionId) {
    // Filter by session when present to keep context scoped.
    query = query.eq("session_id", intent.sessionId);
  }

  const { data, error } = await query;

  if (error) {
    return {
      error: `supabase_memory_fetch_failed:${error.message}`,
      status: "error",
    };
  }

  if (!data || data.length === 0) {
    return { contextItems: [], status: "ok" };
  }

  const contextItems: MemoryContextResponse[] = data
    .map((row) => {
      const {
        content: contentValue,
        created_at: createdAt,
        id,
        session_id: sessionId,
      } = row as MemoryTurnRow;
      const source = sessionId ? `supabase:memories:${sessionId}` : "supabase:memories";

      // Extract text content from JSONB content field
      let context = "";
      if (typeof contentValue === "string") {
        context = contentValue;
      } else if (contentValue && typeof contentValue === "object") {
        // Handle JSONB content - extract text if it's a structured object
        const contentObj = contentValue as Record<string, unknown>;
        context =
          typeof contentObj.text === "string" ? contentObj.text : String(contentValue);
      }

      return {
        context,
        createdAt,
        id,
        score: 1,
        source,
      };
    })
    .filter((item) => item.context.length > 0);

  return {
    contextItems,
    status: "ok",
  };
}

async function handleOnTurnCommitted(
  supabase: AdminClient,
  intent: Extract<MemoryIntent, { type: "onTurnCommitted" }>
): Promise<MemoryAdapterExecutionResult> {
  try {
    // Ensure session exists
    const { data: sessionData, error: sessionError } = await supabase
      .schema("memories")
      .from("sessions")
      .select("id")
      .eq("id", intent.sessionId)
      .eq("user_id", intent.userId)
      .single();

    if (sessionError && sessionError.code !== "PGRST116") {
      // PGRST116 is "not found" - we'll create the session below
      return {
        error: `supabase_session_check_failed:${sessionError.message}`,
        status: "error",
      };
    }

    // Create session if it doesn't exist
    if (!sessionData) {
      const { error: createError } = await supabase
        .schema("memories")
        .from("sessions")
        .insert({
          id: intent.sessionId,
          metadata: {},
          title: intent.turn.content.substring(0, 100) || "Untitled session",
          // biome-ignore lint/style/useNamingConvention: database column uses snake_case
          user_id: intent.userId,
        });

      if (createError) {
        return {
          error: `supabase_session_create_failed:${createError.message}`,
          status: "error",
        };
      }
    }

    // Insert turn
    const turnInsert = {
      attachments: (intent.turn.attachments ||
        []) as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["attachments"],
      // Convert string content to JSONB format: { text: string }
      content: {
        text: intent.turn.content,
      } as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["content"],
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      pii_scrubbed: false,
      role: intent.turn.role,
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      session_id: intent.sessionId,
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      tool_calls: (intent.turn.toolCalls ||
        []) as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["tool_calls"],
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      tool_results: (intent.turn.toolResults ||
        []) as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["tool_results"],
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      user_id: intent.userId,
    };

    const { error: turnError } = await supabase
      .schema("memories")
      .from("turns")
      .insert(turnInsert);

    if (turnError) {
      return {
        error: `supabase_turn_insert_failed:${turnError.message}`,
        status: "error",
      };
    }

    // Update session last_synced_at
    await supabase
      .schema("memories")
      .from("sessions")
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      .update({ last_synced_at: new Date().toISOString() })
      .eq("id", intent.sessionId);

    return { status: "ok" };
  } catch (error) {
    return {
      error: `supabase_on_turn_committed_failed:${error instanceof Error ? error.message : String(error)}`,
      status: "error",
    };
  }
}

async function handleSyncSession(
  supabase: AdminClient,
  intent: Extract<MemoryIntent, { type: "syncSession" }>
): Promise<MemoryAdapterExecutionResult> {
  try {
    // Update session last_synced_at
    const { error } = await supabase
      .schema("memories")
      .from("sessions")
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      .update({ last_synced_at: new Date().toISOString() })
      .eq("id", intent.sessionId)
      .eq("user_id", intent.userId);

    if (error) {
      return {
        error: `supabase_sync_session_failed:${error.message}`,
        status: "error",
      };
    }

    return { status: "ok" };
  } catch (error) {
    return {
      error: `supabase_sync_session_failed:${error instanceof Error ? error.message : String(error)}`,
      status: "error",
    };
  }
}

/**
 * Create Supabase memory adapter.
 *
 * Uses the service-role client for robust background-friendly writes while
 * still enforcing per-user scoping in queries. Handles all memory intents
 * against the canonical memories schema.
 */
export function createSupabaseMemoryAdapter(): MemoryAdapter {
  return {
    async handle(
      intent: MemoryIntent,
      ctx: MemoryAdapterContext
    ): Promise<MemoryAdapterExecutionResult> {
      const supabase = createAdminSupabase();

      if (intent.type === "fetchContext") {
        return await handleFetchContext(supabase, intent);
      }

      if (intent.type === "onTurnCommitted") {
        return await handleOnTurnCommitted(supabase, intent);
      }

      if (intent.type === "syncSession") {
        return await handleSyncSession(supabase, intent);
      }

      // backfillSession can be handled similarly to syncSession
      if (intent.type === "backfillSession") {
        return await handleSyncSession(supabase, {
          ...intent,
          type: "syncSession",
        });
      }

      ctx.now();
      return { status: "skipped" };
    },
    id: "supabase",
    supportedIntents: [
      "fetchContext",
      "onTurnCommitted",
      "syncSession",
      "backfillSession",
    ],
  };
}
