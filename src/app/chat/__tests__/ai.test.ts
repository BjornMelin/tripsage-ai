/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { submitChatMessage } from "../ai";

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: vi.fn(async () => ({ data: { user: { id: "user-1" } } })),
    },
  })),
}));

vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({
    model: () => "ok",
    modelId: "test-model",
    provider: "openai",
  })),
}));

vi.mock("ai", async () => {
  const actual = await vi.importActual("ai");
  return {
    ...actual,
    convertToModelMessages: vi.fn((messages) => messages),
    streamText: vi.fn(async () => ({
      response: { messages: [] },
      // biome-ignore lint/suspicious/useAwait: Generator for testing async iteration
      textStream: (async function* () {
        yield "Hello";
        yield " world";
      })(),
    })),
  };
});

describe("submitChatMessage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns assistant message with aggregated text", async () => {
    const result = await submitChatMessage({ messages: [], text: "Hi" });

    expect(result.userMessage.role).toBe("user");
    expect(result.assistantMessage.role).toBe("assistant");
    const textPart = result.assistantMessage.parts?.find((p) => p.type === "text");
    expect(textPart).toBeDefined();
    expect((textPart as { text?: string }).text).toBe("Hello world");
  });

  it("rejects empty input", async () => {
    await expect(submitChatMessage({ messages: [], text: " " })).rejects.toThrow(
      /Message is required/
    );
  });
});
