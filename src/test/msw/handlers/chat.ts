/**
 * @fileoverview MSW handlers for chat API endpoints.
 *
 * Provides default mock responses for:
 * - /api/chat/sessions
 * - /api/chat
 */

import { HttpResponse, http } from "msw";
import type { Database } from "@/lib/supabase/database.types";
import { createMockUiMessageStreamResponse } from "@/test/ai-sdk/stream-utils";
import { MSW_FIXED_ISO_DATE } from "../constants";

type ChatSessionRow = Database["public"]["Tables"]["chat_sessions"]["Row"];
type ChatSessionListItem = Pick<
  ChatSessionRow,
  "created_at" | "id" | "metadata" | "updated_at"
>;
type ChatSessionsListResponse = ChatSessionListItem[];
type CreateChatSessionResponse = { id: string };

/**
 * Default chat handlers providing happy-path responses.
 */
export const chatHandlers = [
  // GET /api/chat/sessions - List chat sessions
  http.get("/api/chat/sessions", () => {
    return HttpResponse.json<ChatSessionsListResponse>([
      {
        // biome-ignore lint/style/useNamingConvention: match persisted schema fields
        created_at: MSW_FIXED_ISO_DATE,
        id: "session-1",
        metadata: { title: "Mock Session" },
        // biome-ignore lint/style/useNamingConvention: match persisted schema fields
        updated_at: MSW_FIXED_ISO_DATE,
      },
    ]);
  }),

  // POST /api/chat/sessions - Create chat session
  http.post("/api/chat/sessions", () => {
    return HttpResponse.json<CreateChatSessionResponse>({ id: "new-session-id" });
  }),

  // POST /api/chat - UI message stream protocol (stubbed)
  http.post("/api/chat", () => {
    const res = createMockUiMessageStreamResponse({
      finishReason: "stop",
      messageId: "msg-mock-1",
      textChunks: ["Mock response"],
    });
    res.headers.set("x-vercel-ai-ui-message-stream", "v1");
    return res;
  }),
];
