/**
 * @fileoverview Unit test for the demo streaming route. Mocks AI SDK to avoid
 * network calls and asserts an SSE-compatible response shape.
 */
import { describe, expect, it, vi } from "vitest";

// Mock the `ai` package to avoid network/model dependencies
vi.mock("ai", () => {
  return {
    streamText: vi.fn(() => {
      return {
        toUIMessageStreamResponse: () =>
          new Response('data: {"type":"finish"}\n\n', {
            headers: { "content-type": "text/event-stream" },
          }),
      };
    }),
  };
});

// Import after mocks are set up
import { POST } from "@/app/api/_health/stream/route";

describe("_health stream route", () => {
  it("returns an SSE response", async () => {
    const res = await POST(new Request("http://localhost", { method: "POST" }));
    expect(res).toBeInstanceOf(Response);
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toMatch(/text\/event-stream/i);
  });
});
