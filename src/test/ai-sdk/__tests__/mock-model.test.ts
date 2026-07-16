/** @vitest-environment node */

import { generateText, streamText, tool } from "ai";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import {
  createMockModel,
  createStreamingMockModel,
  createStreamingToolMockModel,
} from "../mock-model";

describe("ai-sdk test helpers: mock-model", () => {
  it("supports generateText() with a configured text response", async () => {
    const model = createMockModel({ text: "Hello from AI!" });
    expect(model.specificationVersion).toBe("v4");
    const result = await generateText({ model, prompt: "Say hello" });
    expect(result.text).toBe("Hello from AI!");
  });

  it("supports streamText() with deterministic chunks", async () => {
    const model = createStreamingMockModel({ chunks: ["Hello", " ", "World"] });
    const result = streamText({ model, prompt: "Greet me" });

    let text = "";
    for await (const chunk of result.textStream) {
      text += chunk;
    }

    expect(text).toBe("Hello World");
  });

  it("streams complete V4 tool calls", async () => {
    const result = streamText({
      model: createStreamingToolMockModel({
        toolCalls: [
          {
            args: { location: "Paris" },
            toolCallId: "call-1",
            toolName: "weather",
          },
        ],
      }),
      prompt: "Check the weather",
      tools: {
        weather: tool({
          inputSchema: z.object({ location: z.string() }),
        }),
      },
    });

    await result.consumeStream();

    await expect(result.toolCalls).resolves.toEqual([
      {
        input: { location: "Paris" },
        toolCallId: "call-1",
        toolName: "weather",
        type: "tool-call",
      },
    ]);
  });
});
