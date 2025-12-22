/**
 * @fileoverview MSW handlers for chat API endpoints.
 *
 * Provides default mock responses for:
 * - /api/chat/sessions
 * - /api/chat/stream
 */

import { HttpResponse, http } from "msw";
import { MSW_FIXED_ISO_DATE } from "../constants";

/**
 * Default chat handlers providing happy-path responses.
 */
export const chatHandlers = [
  // GET /api/chat/sessions - List chat sessions
  http.get("/api/chat/sessions", () => {
    return HttpResponse.json({
      sessions: [
        {
          // biome-ignore lint/style/useNamingConvention: match persisted schema fields
          created_at: MSW_FIXED_ISO_DATE,
          id: "session-1",
          title: "Mock Session",
        },
      ],
    });
  }),

  // POST /api/chat/sessions - Create chat session
  http.post("/api/chat/sessions", () => {
    return HttpResponse.json({
      // biome-ignore lint/style/useNamingConvention: match persisted schema fields
      created_at: MSW_FIXED_ISO_DATE,
      id: "new-session-id",
      title: "New Mock Session",
    });
  }),

  // POST /api/chat/stream - Streaming chat endpoint (stubbed as immediate response)
  http.post("/api/chat/stream", () => {
    return new HttpResponse("streamed mock content", {
      headers: { "Content-Type": "text/plain" },
      status: 200,
    });
  }),

  // GET /api/chat/stream - stream fetch in tests
  http.get("/api/chat/stream", () => {
    return new HttpResponse("streamed mock content", {
      headers: { "Content-Type": "text/plain" },
      status: 200,
    });
  }),
];
