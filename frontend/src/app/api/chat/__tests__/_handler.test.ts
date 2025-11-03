/* @vitest-environment node */
/**
 * @fileoverview Unit tests for handleChatNonStream covering auth, attachments, clamping,
 * and usage mapping using injected dependencies and mocked AI SDK interactions.
 */

import type { LanguageModel } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  NonStreamDeps,
  NonStreamPayload,
  ProviderResolver,
} from "@/app/api/chat/_handler";

let handleChatNonStream: (
  deps: NonStreamDeps,
  payload: NonStreamPayload
) => Promise<Response>;

const createResolver =
  (modelId: string): ProviderResolver =>
  async () => ({
    model: {} as LanguageModel,
    modelId,
    provider: "openai",
  });

/**
 * Creates a mock Supabase client for testing handleChatNonStream functionality.
 *
 * @param userId - User ID for authentication mocking, or null for unauthenticated.
 * @param memories - Array of memory content strings for memory hydration testing.
 * @returns Mock Supabase client with basic database operations.
 */
function fakeSupabase(
  userId: string | null,
  memories: string[] = []
): NonStreamDeps["supabase"] {
  return {
    auth: {
      getUser: vi.fn(async () => ({ data: { user: userId ? { id: userId } : null } })),
    },
    from: vi.fn((table: string) => {
      if (table === "memories") {
        return {
          eq: vi.fn().mockReturnThis(),
          limit: vi
            .fn()
            .mockResolvedValue({ data: memories.map((m) => ({ content: m })) }),
          order: vi.fn().mockReturnThis(),
          select: vi.fn().mockReturnThis(),
        };
      }
      if (table === "chat_messages") {
        return {
          insert: vi.fn(async () => ({ error: null })),
        };
      }
      return {};
    }),
  } as unknown as NonStreamDeps["supabase"];
}

describe("handleChatNonStream", () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.doMock("ai", () => ({
      convertToModelMessages: (x: unknown) => x,
      generateText: vi.fn(),
    }));
    ({ handleChatNonStream } = await import("../_handler"));
  });

  it("401 when unauthenticated", async () => {
    const res = await handleChatNonStream(
      { resolveProvider: createResolver("gpt-4o-mini"), supabase: fakeSupabase(null) },
      { messages: [] }
    );
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.error).toBe("unauthorized");
  });

  it("400 on invalid attachment type", async () => {
    const res = await handleChatNonStream(
      {
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u2"),
      },
      {
        messages: [
          {
            id: "m1",
            parts: [
              { text: "hi", type: "text" },
              { mediaType: "application/pdf", type: "file", url: "https://x/y.pdf" },
            ],
            role: "user",
          },
        ],
      }
    );
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("invalid_attachment");
  });

  it("400 when clamp leaves no tokens", async () => {
    const huge = "x".repeat(600_000);
    const res = await handleChatNonStream(
      {
        config: { defaultMaxTokens: 1024 },
        resolveProvider: createResolver("some-unknown-model"),
        supabase: fakeSupabase("u3"),
      },
      {
        messages: [{ id: "u", parts: [{ text: huge, type: "text" }], role: "user" }],
      }
    );
    expect(res.status).toBe(400);
    await res.text();
  });

  it("200 with content and usage mapping", async () => {
    const supabase = fakeSupabase("u4");
    const generateText = vi.fn(async () => ({
      content: [],
      experimental_providerMetadata: undefined,
      experimental_stream: undefined,
      finishReason: "stop",
      messages: [],
      reasoning: [],
      reasoningText: "",
      text: "Hello world",
      toolCalls: [],
      usage: { inputTokens: 10, outputTokens: 32, totalTokens: 42 },
      warnings: [],
    })) as unknown as NonStreamDeps["generate"];
    const res = await handleChatNonStream(
      {
        clock: { now: () => 1000 },
        config: { defaultMaxTokens: 256 },
        generate: generateText,
        logger: { error: vi.fn(), info: vi.fn() },
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase,
      },
      {
        messages: [{ id: "u1", parts: [{ text: "hi", type: "text" }], role: "user" }],
      }
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.content).toBe("Hello world");
    expect(body.model).toBe("gpt-4o-mini");
    expect(body.usage.totalTokens).toBe(42);
    expect(body.usage.promptTokens).toBe(10);
    expect(body.usage.completionTokens).toBe(32);
  });
});
