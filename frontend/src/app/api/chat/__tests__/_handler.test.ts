/** @vitest-environment node */

import type { LanguageModel } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  NonStreamDeps,
  NonStreamPayload,
  ProviderResolver,
} from "@/app/api/chat/_handler";
import type { ProviderId } from "@/lib/schemas/providers";

let handleChatNonStream: (
  deps: NonStreamDeps,
  payload: NonStreamPayload
) => Promise<Response>;

const createResolver =
  (modelId: string): ProviderResolver =>
  async () => ({
    model: {} as LanguageModel,
    modelId,
    provider: "openai" as ProviderId,
  });

const handleMemoryIntentMock = vi.fn();
vi.mock("@/lib/memory/orchestrator", () => ({
  handleMemoryIntent: handleMemoryIntentMock,
}));

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
    handleMemoryIntentMock.mockReset();
    handleMemoryIntentMock.mockResolvedValue({ context: [] });
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
      experimentalProviderMetadata: undefined,
      experimentalStream: undefined,
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

  it("respects model override in payload", async () => {
    const resolveProvider = vi.fn((_userId: string, modelHint?: string) => {
      expect(modelHint).toBe("claude-3.5-sonnet");
      return Promise.resolve({
        model: {} as LanguageModel,
        modelId: "claude-3.5-sonnet",
        provider: "anthropic" as ProviderId,
      });
    });
    const generateText = vi.fn(async () => ({
      content: [],
      experimentalProviderMetadata: undefined,
      experimentalStream: undefined,
      finishReason: "stop",
      messages: [],
      reasoning: [],
      reasoningText: "",
      text: "Response",
      toolCalls: [],
      usage: { inputTokens: 5, outputTokens: 10, totalTokens: 15 },
      warnings: [],
    })) as unknown as NonStreamDeps["generate"];
    const res = await handleChatNonStream(
      {
        generate: generateText,
        resolveProvider,
        supabase: fakeSupabase("u5"),
      },
      {
        messages: [{ id: "u1", parts: [{ text: "hi", type: "text" }], role: "user" }],
        model: "claude-3.5-sonnet",
      }
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.model).toBe("claude-3.5-sonnet");
    expect(resolveProvider).toHaveBeenCalledWith("u5", "claude-3.5-sonnet");
  });

  it("handles provider resolution failure gracefully", async () => {
    const resolveProvider = vi.fn(() => {
      throw new Error("Provider resolution failed");
    });
    const logger = { error: vi.fn(), info: vi.fn() };
    // Provider resolution failure should propagate as an error
    // The handler doesn't catch this, so it will throw
    await expect(
      handleChatNonStream(
        {
          logger,
          resolveProvider,
          supabase: fakeSupabase("u6"),
        },
        {
          messages: [{ id: "u1", parts: [{ text: "hi", type: "text" }], role: "user" }],
        }
      )
    ).rejects.toThrow("Provider resolution failed");
  });

  it("429 when rate limited", async () => {
    const limit = vi.fn(async () => ({ success: false })) as NonStreamDeps["limit"];
    const res = await handleChatNonStream(
      {
        limit,
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u7"),
      },
      { ip: "1.2.3.4", messages: [] }
    );
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
    const body = await res.json();
    expect(body.error).toBe("rate_limited");
  });

  it("emits memory intents for user and assistant turns when sessionId is present", async () => {
    handleMemoryIntentMock.mockImplementation((intent) => {
      if ((intent as { type?: string }).type === "fetchContext") {
        return { context: [] };
      }
      return { status: "ok" };
    });

    const generateText = vi.fn(async () => ({
      content: [],
      experimentalProviderMetadata: undefined,
      experimentalStream: undefined,
      finishReason: "stop",
      messages: [],
      reasoning: [],
      reasoningText: "",
      text: "Itinerary ready",
      toolCalls: [],
      usage: { inputTokens: 12, outputTokens: 24, totalTokens: 36 },
      warnings: [],
    })) as unknown as NonStreamDeps["generate"];

    await handleChatNonStream(
      {
        generate: generateText,
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u8"),
      },
      {
        messages: [
          {
            id: "u1",
            parts: [{ text: "remember my window seat", type: "text" }],
            role: "user",
          },
        ],
        sessionId: "sess-1",
      }
    );

    const intents = handleMemoryIntentMock.mock.calls
      .map(([intent]) => intent as Record<string, unknown>)
      .filter((intent) => intent?.type === "onTurnCommitted");

    expect(intents).toHaveLength(2);
    expect(intents[0]).toMatchObject({
      sessionId: "sess-1",
      turn: { content: "remember my window seat", role: "user" },
      userId: "u8",
    });
    expect(intents[1]).toMatchObject({
      sessionId: "sess-1",
      turn: { content: "Itinerary ready", role: "assistant" },
      userId: "u8",
    });
  });
});
