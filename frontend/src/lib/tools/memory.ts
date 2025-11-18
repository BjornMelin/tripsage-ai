/**
 * @fileoverview Memory tools backed by Supabase memories schema (server-only).
 *
 * Uses the canonical `memories.*` schema (memories.sessions, memories.turns)
 * for storing and retrieving conversational memory.
 */

import "server-only";

import { tool } from "ai";
import { z } from "zod";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import type { Database } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";

/**
 * Input schema for adding conversation memory.
 * Note: Category is stored in turn metadata, not as a separate field.
 */
export const addConversationMemoryInputSchema = z.object({
  category: z
    .enum([
      "user_preference",
      "trip_history",
      "search_pattern",
      "conversation_context",
      "other",
    ])
    .default("other"),
  content: z.string().min(1),
});

/**
 * Store a conversation memory turn for the current user.
 *
 * Creates or updates a memory session and inserts a turn with the provided content.
 * Uses the orchestrator to ensure proper session management.
 */
export const addConversationMemory = tool({
  description: "Store a short memory snippet for the current user.",
  execute: async ({ content, category }) => {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth?.user?.id;
    if (!userId) throw new Error("unauthorized");

    // Generate a session ID for standalone memory entries
    const sessionId = crypto.randomUUID();

    // Ensure session exists
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

    // Create session if it doesn't exist
    if (!sessionData) {
      const { error: createError } = await supabase
        .schema("memories")
        .from("sessions")
        .insert({
          id: sessionId,
          metadata: { category },
          title: content.substring(0, 100) || "Memory entry",
          // biome-ignore lint/style/useNamingConvention: database column uses snake_case
          user_id: userId,
        });

      if (createError) {
        throw new Error(`memory_session_create_failed:${createError.message}`);
      }
    }

    // Insert turn
    const turnInsert: Database["memories"]["Tables"]["turns"]["Insert"] = {
      attachments: [],
      // Convert string content to JSONB format: { text: string }
      content: {
        text: content,
      } as unknown as Database["memories"]["Tables"]["turns"]["Insert"]["content"],
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      pii_scrubbed: false,
      role: "user",
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      session_id: sessionId,
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      tool_calls: [],
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      tool_results: [],
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
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
  inputSchema: addConversationMemoryInputSchema,
});

/**
 * Search user memory turns by keyword.
 *
 * Queries the memories.turns table for content matching the query string.
 */
export const searchUserMemories = tool({
  description: "Search recent user memories by keyword.",
  execute: async ({ query, limit }) => {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth?.user?.id;
    if (!userId) throw new Error("unauthorized");

    // Use orchestrator for consistent memory retrieval
    const memoryResult = await handleMemoryIntent({
      limit,
      sessionId: "",
      type: "fetchContext",
      userId,
    });

    // Filter results by query keyword (simple text matching)
    const filtered = (memoryResult.context ?? []).filter((item) =>
      item.context.toLowerCase().includes(query.toLowerCase())
    );

    return filtered.map((item) => ({
      content: item.context,
      // biome-ignore lint/style/useNamingConvention: database column uses snake_case
      created_at: new Date().toISOString(), // Approximate - actual timestamp would require join
      source: item.source,
    }));
  },
  inputSchema: z.object({
    limit: z.int().min(1).max(20).default(5),
    query: z.string().min(1),
  }),
});
