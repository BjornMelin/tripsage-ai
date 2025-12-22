/**
 * @fileoverview MSW handlers for internal AI routes used in tests.
 *
 * These are application routes (e.g. demo endpoints), not upstream provider APIs.
 * Upstream provider mocks live in `ai-providers.ts`.
 */

import { HttpResponse, http } from "msw";

export const aiRouteHandlers = [
  // POST /api/ai/stream - AI streaming endpoint for demo
  http.post("/api/ai/stream", () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode('data: {"type":"text","text":"Hello from AI"}\n\n')
        );
        controller.close();
      },
    });

    return new HttpResponse(stream, {
      headers: { "Content-Type": "text/event-stream" },
      status: 200,
    });
  }),
];
