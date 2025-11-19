/**
 * @fileoverview Memory tools backed by Supabase memories schema (server-only).
 *
 * Uses the canonical `memories.*` schema (memories.sessions, memories.turns)
 * for storing and retrieving conversational memory.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import {
  addConversationMemoryInputSchema,
  searchUserMemoriesInputSchema,
} from "@schemas/memory";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import type { Database } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";

/**
 * Tool for adding a conversation memory snippet to the user's memory.
 *
 * Stores a short memory snippet in the user's memory for later retrieval.
 * Returns the memory ID and creation timestamp.
 *
 * @param content Memory snippet content.
 * @param category Memory category (user preference, trip history, search pattern, conversation context, other).
 * @returns Promise resolving to memory ID and creation timestamp.
 */
export const addConversationMemory = createAiTool({
  description: "Store a short memory snippet for the current user.",
  execute: async ({ content, category }) => {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth?.user?.id;
    if (!userId) throw new Error("unauthorized");

    const sessionId = crypto.randomUUID();

    const { data: sessionData, error: sessionError } = await supabase
      .schema("memories")
      .from("sessions")
      .select("id")
      .eq("id", sessionId)
      .eq("user_id", userId)
      .single();

    if (sessionError && sessionError.code !== "PGRST116") {
      throw new Error(`memory_session_check_failed:${sessionError.message}`);
    }

    if (!sessionData) {
      const { error: createError } = await supabase
        .schema("memories")
        .from("sessions")
        .insert({
          id: sessionId,
          metadata: { category },
          title: content.substring(0, 100) || "Memory entry",
          // biome-ignore lint/style/useNamingConvention: Database field name
          user_id: userId,
        });

      if (createError) {
        throw new Error(`memory_session_create_failed:${createError.message}`);
      }
    }

    const turnInsert: Database["memories"]["Tables"]["turns"]["Insert"] = {
      attachments: [],
      // biome-ignore lint/suspicious/noExplicitAny: Database schema type
      content: { text: content } as any,
      // biome-ignore lint/style/useNamingConvention: Database field name
      pii_scrubbed: false,
      role: "user",
      // biome-ignore lint/style/useNamingConvention: Database field name
      session_id: sessionId,
      // biome-ignore lint/style/useNamingConvention: Database field name
      tool_calls: [],
      // biome-ignore lint/style/useNamingConvention: Database field name
      tool_results: [],
      // biome-ignore lint/style/useNamingConvention: Database field name
      user_id: userId,
    };

    const { data: turnData, error: turnError } = await supabase
      .schema("memories")
      .from("turns")
      .insert(turnInsert)
      .select("id, created_at")
      .single();

    if (turnError) {
      throw new Error(`memory_turn_insert_failed:${turnError.message}`);
    }

    return {
      createdAt: turnData.created_at,
      id: turnData.id,
    };
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      window: "1 m",
    },
  },
  inputSchema: addConversationMemoryInputSchema,
  name: "addConversationMemory",
});

/**
 * Tool for searching the user's recent memories by keyword.
 *
 * Searches the user's recent memories for items containing the specified keyword.
 * Returns a list of matching memory items with content, creation timestamp, and source.
 *
 * @param query Search keyword.
 * @param limit Maximum number of memories to return.
 * @returns Promise resolving to list of matching memory items.
 */
export const searchUserMemories = createAiTool({
  description: "Search recent user memories by keyword.",
  execute: async ({ query, limit }) => {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth?.user?.id;
    if (!userId) throw new Error("unauthorized");

    const memoryResult = await handleMemoryIntent({
      limit,
      sessionId: "",
      type: "fetchContext",
      userId,
    });

    const filtered = (memoryResult.context ?? []).filter((item) =>
      item.context.toLowerCase().includes(query.toLowerCase())
    );

    return filtered.map((item) => ({
      content: item.context,
      // biome-ignore lint/style/useNamingConvention: Database field name
      created_at: new Date().toISOString(),
      source: item.source,
    }));
  },
  guardrails: {
    cache: {
      key: (p) => JSON.stringify(p),
      ttlSeconds: 60,
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      window: "1 m",
    },
  },
  inputSchema: searchUserMemoriesInputSchema,
  name: "searchUserMemories",
});
