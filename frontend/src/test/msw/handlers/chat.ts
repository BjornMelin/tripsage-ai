/**
 * @fileoverview MSW handlers for chat API endpoints.
 *
 * Provides default mock responses for:
 * - /api/chat
 * - /api/chat/sessions
 * - /api/chat/stream
 */

import { HttpResponse, http } from "msw";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

/**
 * Default chat handlers providing happy-path responses.
 */
export const chatHandlers = [
  // POST /api/chat - Chat message endpoint
  http.post(`${BASE_URL}/api/chat`, () => {
    return HttpResponse.json({
      content: "This is a mock chat response",
      model: "gpt-4o-mini",
      usage: {
        completionTokens: 20,
        promptTokens: 10,
        totalTokens: 30,
      },
    });
  }),

  // GET /api/chat/sessions - List chat sessions
  http.get(`${BASE_URL}/api/chat/sessions`, () => {
    return HttpResponse.json({
      sessions: [
        {
          // biome-ignore lint/style/useNamingConvention: match persisted schema fields
          created_at: new Date().toISOString(),
          id: "session-1",
          title: "Mock Session",
        },
      ],
    });
  }),

  // POST /api/chat/sessions - Create chat session
  http.post(`${BASE_URL}/api/chat/sessions`, () => {
    return HttpResponse.json({
      // biome-ignore lint/style/useNamingConvention: match persisted schema fields
      created_at: new Date().toISOString(),
      id: "new-session-id",
      title: "New Mock Session",
    });
  }),

  // POST /api/chat/stream - Streaming chat endpoint (stubbed as immediate response)
  http.post(`${BASE_URL}/api/chat/stream`, () => {
    return new HttpResponse("streamed mock content", {
      headers: { "Content-Type": "text/plain" },
      status: 200,
    });
  }),

  // GET /api/chat/stream - stream fetch in tests
  http.get(`${BASE_URL}/api/chat/stream`, () => {
    return new HttpResponse("streamed mock content", {
      headers: { "Content-Type": "text/plain" },
      status: 200,
    });
  }),

  // fallback relative handlers
  http.post("/api/chat/stream", () => {
    return new HttpResponse("streamed mock content", {
      headers: { "Content-Type": "text/plain" },
      status: 200,
    });
  }),
  http.get("/api/chat/stream", () => {
    return new HttpResponse("streamed mock content", {
      headers: { "Content-Type": "text/plain" },
      status: 200,
    });
  }),
];
