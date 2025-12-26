/** @vitest-environment node */

import { generateText, streamText } from "ai";
import { describe, expect, it } from "vitest";
import { createMockModel, createStreamingMockModel } from "../mock-model";

describe("ai-sdk test helpers: mock-model", () => {
  it("supports generateText() with a configured text response", async () => {
    const model = createMockModel({ text: "Hello from AI!" });
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
});
