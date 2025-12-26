/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import {
  collectStreamChunks,
  collectStreamChunksArray,
  createMockAiStreamResponse,
  createMockStreamResponse,
  createMockUiMessageStreamResponse,
} from "../stream-utils";

describe("ai-sdk test helpers: stream-utils", () => {
  it("collects chunks from a mock ReadableStream", async () => {
    const stream = createMockStreamResponse({ chunks: ["a", "b", "c"] });
    await expect(collectStreamChunks(stream)).resolves.toBe("abc");
  });

  it("collects chunks into an array", async () => {
    const stream = createMockStreamResponse({ chunks: ["x", "y"] });
    await expect(collectStreamChunksArray(stream)).resolves.toEqual(["x", "y"]);
  });

  it("creates an AI-like SSE stream response", async () => {
    const stream = createMockAiStreamResponse({ textChunks: ["Hi", " there"] });
    const payload = await collectStreamChunks(stream);
    expect(payload).toContain("data:");
    expect(payload).toContain("[DONE]");
  });

  it("creates a UI message stream Response", async () => {
    const response = createMockUiMessageStreamResponse({
      finishReason: "stop",
      textChunks: ["Hello"],
    });
    const text = await response.text();
    expect(text).toContain('"type":"start"');
    expect(text).toContain('"type":"finish"');
    expect(text).toContain("[DONE]");
  });
});
