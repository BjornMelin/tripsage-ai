/**
 * @fileoverview Memory adapter backed by Supabase `memories.*` tables.
 *
 * Supports both recency-based and semantic search retrieval:
 * - When a query is provided, uses pgvector similarity search via match_turn_embeddings RPC
 * - When no query is provided, falls back to recency-based retrieval
 */

import "server-only";

import { openai } from "@ai-sdk/openai";
import type { MemoryContextResponse } from "@schemas/chat";
import { jsonSchema } from "@schemas/supabase";
import type { SupabaseClient } from "@supabase/supabase-js";
import { embed } from "ai";
import { toPgvector } from "@/lib/rag/pgvector";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import { createServerLogger } from "@/lib/telemetry/logger";
import type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryIntent,
} from "./types";

const logger = createServerLogger("memory.supabase-adapter");

type AdminClient = SupabaseClient<Database>;
type MemoryTurnRow = Database["memories"]["Tables"]["turns"]["Row"];

const MAX_CONTEXT_ITEMS = 10;
const DEFAULT_SIMILARITY_THRESHOLD = 0.7;

/**
 * Semantic search over turn embeddings using pgvector.
 *
 * Generates an embedding for the query and searches for similar turns
 * using the match_turn_embeddings RPC function.
 */
async function handleSemanticFetchContext(
  supabase: AdminClient,
  intent: Extract<MemoryIntent, { type: "fetchContext" }> & { query: string }
): Promise<MemoryAdapterExecutionResult> {
  const limit = intent.limit && intent.limit > 0 ? intent.limit : MAX_CONTEXT_ITEMS;

  try {
    // Generate query embedding using OpenAI text-embedding-3-small (1536-d)
    const { embedding } = await embed({
      model: openai.embeddingModel("text-embedding-3-small"),
      value: intent.query,
    });

    if (embedding.length !== 1536) {
      logger.warn("embedding_dimension_mismatch", {
        expected: 1536,
        got: embedding.length,
      });
      // Fall back to recency-based search
      return handleRecencyFetchContext(supabase, intent);
    }

    // Call the match_turn_embeddings RPC function
    const { data, error } = await supabase.rpc("match_turn_embeddings", {
      // biome-ignore lint/style/useNamingConvention: RPC parameter name
      filter_session_id: intent.sessionId || null,
      // biome-ignore lint/style/useNamingConvention: RPC parameter name
      filter_user_id: intent.userId,
      // biome-ignore lint/style/useNamingConvention: RPC parameter name
      match_count: limit,
      // biome-ignore lint/style/useNamingConvention: RPC parameter name
      match_threshold: DEFAULT_SIMILARITY_THRESHOLD,
      // biome-ignore lint/style/useNamingConvention: RPC parameter name
      query_embedding: toPgvector(embedding),
    });

    if (error) {
      logger.warn("semantic_search_failed", { error: error.message });
      // Fall back to recency-based search on RPC error
      return handleRecencyFetchContext(supabase, intent);
    }

    if (!data || data.length === 0) {
      return { contextItems: [], status: "ok" };
    }

    const contextItems: MemoryContextResponse[] = data
      .map((row) => {
        const contentValue = row.content;
        const sessionId = row.session_id;
        const source = sessionId
          ? `supabase:memories:${sessionId}`
          : "supabase:memories";

        // Extract text content from JSONB content field
        let context = "";
        if (typeof contentValue === "string") {
          context = contentValue;
        } else if (contentValue && typeof contentValue === "object") {
          const contentObj = contentValue as Record<string, unknown>;
          context =
            typeof contentObj.text === "string"
              ? contentObj.text
              : String(contentValue);
        }

        return {
          context,
          createdAt: row.created_at,
          id: row.turn_id,
          score: row.similarity,
          source,
        };
      })
      .filter((item) => item.context.length > 0);

    logger.info("semantic_search_complete", {
      query: intent.query.substring(0, 50),
      resultCount: contextItems.length,
    });

    return {
      contextItems,
      status: "ok",
    };
  } catch (error) {
    logger.warn("semantic_search_error", {
      error: error instanceof Error ? error.message : String(error),
    });
    // Fall back to recency-based search on any error
    return handleRecencyFetchContext(supabase, intent);
  }
}

/**
 * Recency-based context retrieval (original behavior).
 * Fetches most recent turns for a user/session without semantic matching.
 */
async function handleRecencyFetchContext(
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

/**
 * Route fetchContext to semantic or recency-based retrieval.
 *
 * Uses semantic search when a query is provided; otherwise falls back
 * to recency-based retrieval (original behavior).
 */
function handleFetchContext(
  supabase: AdminClient,
  intent: Extract<MemoryIntent, { type: "fetchContext" }>
): Promise<MemoryAdapterExecutionResult> {
  if (intent.query && intent.query.trim().length > 0) {
    return handleSemanticFetchContext(supabase, {
      ...intent,
      query: intent.query,
    });
  }
  return handleRecencyFetchContext(supabase, intent);
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
      attachments: jsonSchema.parse(intent.turn.attachments ?? []),
      // Convert string content to JSONB format: { text: string }
      content: {
        text: intent.turn.content,
      },
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      pii_scrubbed: false,
      role: intent.turn.role,
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      session_id: intent.sessionId,
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      tool_calls: jsonSchema.parse(intent.turn.toolCalls ?? []),
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      tool_results: jsonSchema.parse(intent.turn.toolResults ?? []),
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
