/**
 * @fileoverview Pure handler for memory sync jobs.
 */

import "server-only";

import { jsonSchema } from "@schemas/supabase";
import type { MemorySyncJob } from "@schemas/webhooks";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";

export interface MemorySyncJobDeps {
  supabase: TypedAdminSupabase;
  clock?: { now: () => string };
}

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
  const nowIso = deps.clock?.now ?? (() => new Date().toISOString());
  const MaxConversationBatchSize = 50;

  // Verify user has access to this session
  const { data: session, error: sessionError } = await supabase
    .from("chat_sessions")
    .select("id")
    .eq("id", payload.sessionId)
    .eq("user_id", payload.userId)
    .single();

  if (sessionError || !session) {
    throw new Error("session_not_found_or_unauthorized");
  }

  let memoriesStored = 0;
  let contextUpdated = false;

  // Process conversation messages if provided
  if (payload.conversationMessages && payload.conversationMessages.length > 0) {
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
          // biome-ignore lint/style/useNamingConvention: Database field name
          user_id: payload.userId,
        });

      if (createError) {
        throw new Error(`memory_session_create_failed: ${createError.message}`);
      }
    }

    // Store conversation turns
    const turnInserts: Database["memories"]["Tables"]["turns"]["Insert"][] =
      messagesToStore.map((msg) => ({
        attachments: jsonSchema.parse(msg.metadata?.attachments ?? []),
        // Convert string content to JSONB format: { text: string }
        content: {
          text: msg.content,
        },
        // biome-ignore lint/style/useNamingConvention: Database field name
        pii_scrubbed: false,
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

    const { error: insertError } = await supabase
      .schema("memories")
      .from("turns")
      .insert(turnInserts)
      .select("id");

    if (insertError) {
      throw new Error(`memory_turn_insert_failed: ${insertError.message}`);
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
      throw new Error(`memory_session_sync_update_failed: ${syncError.message}`);
    }

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
        // biome-ignore lint/style/useNamingConvention: Database field name
        memory_synced_at: nowIso(),
        // biome-ignore lint/style/useNamingConvention: Database field name
        updated_at: nowIso(),
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
