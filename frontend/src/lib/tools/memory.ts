/**
 * @fileoverview Memory tools backed by Supabase (server-only).
 */

import { tool } from "ai";
import { z } from "zod";
import type { Database } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";

export const addConversationMemory = tool({
  description: "Store a short memory snippet for the current user.",
  execute: async ({ content, category }) => {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth?.user?.id;
    if (!userId) throw new Error("unauthorized");
    type MemoriesInsert = Database["public"]["Tables"]["memories"]["Insert"];
    type MemoryType = NonNullable<MemoriesInsert["memory_type"]>;
    const allowed: readonly MemoryType[] = [
      "user_preference",
      "trip_history",
      "search_pattern",
      "conversation_context",
      "other",
    ];
    const rawType = (category ?? "other") as string;
    const memoryType: MemoryType = (
      allowed.includes(rawType as MemoryType) ? (rawType as MemoryType) : "other"
    ) as MemoryType;

    const row = Object.fromEntries([
      ["user_id", userId],
      ["content", content],
      ["memory_type", memoryType],
      ["metadata", {}],
    ] as const) as MemoriesInsert;
    type LooseFrom = {
      from: (table: string) => {
        insert: (values: unknown) => {
          select: (cols: string) => {
            single: () => Promise<{
              data: { id: number } & Record<string, unknown>;
              error: { message: string } | null;
            }>;
          };
        };
      };
    };
    const sb = supabase as unknown as LooseFrom;
    const { data, error } = await sb
      .from("memories")
      .insert(row)
      .select("id, created_at")
      .single();
    if (error) throw new Error(`memory_insert_failed:${error.message}`);
    return { createdAt: data.created_at as string, id: (data as { id: number }).id };
  },
  inputSchema: z.object({
    category: z.string().default("general"),
    content: z.string().min(1),
  }),
});

export const searchUserMemories = tool({
  description: "Search recent user memories by keyword.",
  execute: async ({ query, limit }) => {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth?.user?.id;
    if (!userId) throw new Error("unauthorized");
    const { data, error } = await supabase
      .from("memories")
      .select("content, category, created_at")
      .ilike("content", `%${query}%`)
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(limit);
    if (error) throw new Error(`memory_search_failed:${error.message}`);
    return data ?? [];
  },
  inputSchema: z.object({
    limit: z.number().int().min(1).max(20).default(5),
    query: z.string().min(1),
  }),
});
