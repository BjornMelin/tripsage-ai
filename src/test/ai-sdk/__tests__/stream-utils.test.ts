/** @vitest-environment node */

import { uiMessageChunkSchema } from "ai";
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

  it("creates a schema-valid v7 UI message stream Response", async () => {
    const response = createMockUiMessageStreamResponse({
      finishReason: "stop",
      textChunks: ["Hello"],
      toolCalls: [
        {
          input: { query: "london" },
          toolCallId: "tool-1",
          toolName: "webSearch",
        },
      ],
    });
    const text = await response.text();
    expect(text).toContain('"type":"start"');
    expect(text).toContain('"type":"finish"');
    expect(text).toContain('"type":"tool-input-start"');
    expect(text).toContain('"type":"tool-input-delta"');
    expect(text).toContain('"type":"tool-input-available"');
    expect(text).not.toContain('"type":"tool-call-');
    expect(text).toContain("[DONE]");

    const chunks = text
      .split("\n")
      .filter((line) => line.startsWith("data: ") && line !== "data: [DONE]")
      .map((line) => JSON.parse(line.slice(6)) as unknown);
    const schema = uiMessageChunkSchema();
    const validate = schema.validate;
    if (!validate) throw new Error("UI message chunk schema is not validatable");
    for (const chunk of chunks) {
      const result = await validate(chunk);
      expect(result.success).toBe(true);
    }
  });
});
