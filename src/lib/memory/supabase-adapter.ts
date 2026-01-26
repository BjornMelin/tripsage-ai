/**
 * @fileoverview Supabase memory adapter with recency-based retrieval and pgvector semantic search.
 */

import "server-only";

import type { MemoryContextResponse } from "@schemas/chat";
import { jsonSchema } from "@schemas/supabase";
import type { SupabaseClient } from "@supabase/supabase-js";
import { embed } from "ai";
import {
  getTextEmbeddingModel,
  TEXT_EMBEDDING_DIMENSIONS,
} from "@/lib/ai/embeddings/text-embedding-model";
import { toPgvector } from "@/lib/rag/pgvector";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import {
  getMany,
  getMaybeSingle,
  insertSingle,
  updateSingle,
} from "@/lib/supabase/typed-helpers";
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
const EMBED_TIMEOUT_MS = 2_000;

function extractTextFromContent(contentValue: unknown): string {
  if (typeof contentValue === "string") return contentValue;

  if (contentValue && typeof contentValue === "object") {
    const contentObj = contentValue as { text?: unknown };
    if (typeof contentObj.text === "string") return contentObj.text;
    return String(contentValue);
  }

  return "";
}

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
  const similarityThreshold =
    typeof intent.similarityThreshold === "number" &&
    Number.isFinite(intent.similarityThreshold)
      ? Math.min(1, Math.max(0, intent.similarityThreshold))
      : DEFAULT_SIMILARITY_THRESHOLD;

  try {
    // Generate query embedding using the configured embedding provider (AI Gateway/OpenAI),
    // falling back to deterministic offline embeddings when no provider keys are set.
    const { embedding } = await embed({
      abortSignal: AbortSignal.timeout(EMBED_TIMEOUT_MS),
      model: getTextEmbeddingModel(),
      value: intent.query,
    });

    if (embedding.length !== TEXT_EMBEDDING_DIMENSIONS) {
      logger.warn("embedding_dimension_mismatch", {
        expected: TEXT_EMBEDDING_DIMENSIONS,
        got: embedding.length,
      });
      // Fall back to recency-based search
      return handleRecencyFetchContext(supabase, intent);
    }

    // Call the match_turn_embeddings RPC function
    const { data, error } = await supabase
      .schema("memories")
      .rpc("match_turn_embeddings", {
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        filter_session_id: intent.sessionId || undefined,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        filter_user_id: intent.userId,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        match_count: limit,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        match_threshold: similarityThreshold,
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

        const context = extractTextFromContent(contentValue);

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

  const { data, error } = await getMany(
    supabase,
    "turns",
    (qb) => {
      const scoped = intent.sessionId ? qb.eq("session_id", intent.sessionId) : qb;
      return scoped.eq("user_id", intent.userId);
    },
    {
      ascending: false,
      limit,
      orderBy: "created_at",
      schema: "memories",
      select: "id, content, created_at, session_id",
      validate: false,
    }
  );

  if (error) {
    return {
      error: `supabase_memory_fetch_failed:${error instanceof Error ? error.message : String(error)}`,
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

      const context = extractTextFromContent(contentValue);

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
    const { data: sessionData, error: sessionError } = await getMaybeSingle(
      supabase,
      "sessions",
      (qb) => qb.eq("id", intent.sessionId).eq("user_id", intent.userId),
      { schema: "memories", select: "id", validate: false }
    );

    if (sessionError) {
      return {
        error: `supabase_session_check_failed:${sessionError instanceof Error ? sessionError.message : String(sessionError)}`,
        status: "error",
      };
    }

    // Create session if it doesn't exist
    if (!sessionData) {
      const { error: createError } = await insertSingle(
        supabase,
        "sessions",
        {
          id: intent.sessionId,
          metadata: {},
          title: intent.turn.content.substring(0, 100) || "Untitled session",
          // biome-ignore lint/style/useNamingConvention: database column uses snake_case
          user_id: intent.userId,
        },
        { schema: "memories" }
      );

      if (createError) {
        return {
          error: `supabase_session_create_failed:${createError instanceof Error ? createError.message : String(createError)}`,
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

    const { error: turnError } = await insertSingle(supabase, "turns", turnInsert, {
      schema: "memories",
    });

    if (turnError) {
      return {
        error: `supabase_turn_insert_failed:${turnError instanceof Error ? turnError.message : String(turnError)}`,
        status: "error",
      };
    }

    // Update session last_synced_at
    const { error: syncError } = await updateSingle(
      supabase,
      "sessions",
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      { last_synced_at: new Date().toISOString() },
      (qb) => qb.eq("id", intent.sessionId).eq("user_id", intent.userId),
      { schema: "memories", select: "id", validate: false }
    );
    if (syncError) {
      return {
        error: `supabase_session_sync_failed:${syncError instanceof Error ? syncError.message : String(syncError)}`,
        status: "error",
      };
    }

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
    const { error } = await updateSingle(
      supabase,
      "sessions",
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      { last_synced_at: new Date().toISOString() },
      (qb) => qb.eq("id", intent.sessionId).eq("user_id", intent.userId),
      { schema: "memories", select: "id", validate: false }
    );

    if (error) {
      return {
        error: `supabase_sync_session_failed:${error instanceof Error ? error.message : String(error)}`,
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
