/** @vitest-environment node */

import type { ProviderId } from "@schemas/providers";
import type { LanguageModel, UIMessage } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatDeps, ProviderResolver } from "../_handler";

// Mock the chat agent module
vi.mock("@ai/agents", () => ({
  createChatAgent: vi.fn(() => ({
    agent: {
      generate: vi.fn(),
      stream: vi.fn(),
    },
    modelId: "gpt-4o-mini",
  })),
  validateChatMessages: vi.fn(() => ({ valid: true })),
}));

// Mock createAgentUIStreamResponse
const mockCreateAgentUIStreamResponse: ReturnType<typeof vi.fn> = vi.hoisted(() =>
  vi.fn()
);

vi.mock("ai", () => ({
  createAgentUIStreamResponse: mockCreateAgentUIStreamResponse,
}));

// Mock memory functions
vi.mock("@/lib/memory/orchestrator", () => ({
  handleMemoryIntent: vi.fn(async () => ({ context: [] })),
}));

vi.mock("@/lib/memory/turn-utils", () => ({
  assistantResponseToMemoryTurn: vi.fn(() => null),
  persistMemoryTurn: vi.fn(async () => undefined),
  uiMessageToMemoryTurn: vi.fn(() => null),
}));

vi.mock("@/lib/security/random", () => ({
  secureUuid: () => "test-uuid-123",
}));

import { validateChatMessages } from "@ai/agents";
import { handleChatStream } from "../_handler";

const createResolver =
  (modelId: string): ProviderResolver =>
  async () => ({
    model: {} as LanguageModel,
    modelId,
    provider: "openai" as ProviderId,
  });

/**
 * Type for the mock query builder methods used in tests.
 */
type MockQueryBuilder = {
  eq: ReturnType<typeof vi.fn>;
  limit?: ReturnType<typeof vi.fn>;
  order?: ReturnType<typeof vi.fn>;
  select?: ReturnType<typeof vi.fn>;
  insert?: ReturnType<typeof vi.fn>;
  update?: ReturnType<typeof vi.fn>;
};

/**
 * Creates a mock Supabase client for testing handleChatStream functionality.
 *
 * @param userId - User ID for authentication mocking, or null for unauthenticated.
 * @param memories - Array of memory content strings for memory hydration testing.
 * @returns Mock Supabase client with basic database operations.
 */
function fakeSupabase(
  userId: string | null,
  memories: string[] = []
): ChatDeps["supabase"] {
  const mockQueryBuilder = (table: string): MockQueryBuilder => {
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
        eq: vi.fn().mockReturnThis(),
        insert: vi.fn(async () => ({ error: null })),
        limit: vi.fn().mockReturnThis(),
        order: vi.fn().mockReturnThis(),
        select: vi.fn().mockReturnThis(),
      };
    }
    if (table === "chat_sessions") {
      return {
        eq: vi.fn().mockReturnThis(),
        update: vi.fn().mockReturnThis(),
      };
    }
    return {
      eq: vi.fn().mockReturnThis(),
    };
  };

  return {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: userId ? { id: userId } : null },
      })),
    },
    from: vi.fn(mockQueryBuilder),
  } as unknown as ChatDeps["supabase"];
}

describe("handleChatStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateAgentUIStreamResponse.mockResolvedValue(
      new Response("ok", { status: 200 })
    );
  });

  it("401 when unauthenticated", async () => {
    const res = await handleChatStream(
      {
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase(null),
      },
      { messages: [] }
    );
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.error).toBe("unauthorized");
  });

  it("creates agent and streams response for authenticated user", async () => {
    const res = await handleChatStream(
      {
        clock: { now: () => 1000 },
        config: { defaultMaxTokens: 256 },
        logger: { error: vi.fn(), info: vi.fn() },
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u4"),
      },
      {
        messages: [
          {
            id: "m",
            parts: [{ text: "hello", type: "text" }],
            role: "user",
          } satisfies UIMessage,
        ],
        sessionId: "s1",
      }
    );
    expect(res.status).toBe(200);
    expect(mockCreateAgentUIStreamResponse).toHaveBeenCalled();
  });

  it("429 when rate limited", async () => {
    const res = await handleChatStream(
      {
        limit: vi.fn(async () => ({ success: false })) as ChatDeps["limit"],
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u1"),
      },
      { ip: "1.2.3.4", messages: [] }
    );
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
  });

  it("400 on invalid attachment type", async () => {
    // Mock validateChatMessages to return invalid
    vi.mocked(validateChatMessages).mockReturnValueOnce({
      error: "invalid_attachment",
      reason: "Only image attachments are supported",
      valid: false,
    });

    const res = await handleChatStream(
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
              {
                mediaType: "application/pdf",
                type: "file",
                url: "https://x/y.pdf",
              },
            ],
            role: "user",
          } satisfies UIMessage,
        ],
      }
    );
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("invalid_attachment");
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

    const res = await handleChatStream(
      {
        resolveProvider,
        supabase: fakeSupabase("u5"),
      },
      {
        messages: [
          {
            id: "m1",
            parts: [{ text: "hi", type: "text" }],
            role: "user",
          } satisfies UIMessage,
        ],
        model: "claude-3.5-sonnet",
      }
    );
    expect(res.status).toBe(200);
    expect(resolveProvider).toHaveBeenCalledWith("u5", "claude-3.5-sonnet");
  });

  it("calls createAgentUIStreamResponse with agent and messages", async () => {
    const messages: UIMessage[] = [
      {
        id: "m1",
        parts: [{ text: "test message", type: "text" }],
        role: "user",
      },
    ];

    await handleChatStream(
      {
        config: { defaultMaxTokens: 512 },
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u6"),
      },
      {
        desiredMaxTokens: 256,
        messages,
      }
    );

    expect(mockCreateAgentUIStreamResponse).toHaveBeenCalledWith(
      expect.objectContaining({
        agent: expect.anything(),
        messages: expect.anything(),
        onError: expect.any(Function),
        onFinish: expect.any(Function),
      })
    );
  });

  it("handles provider resolution failure", async () => {
    const resolveProvider = vi.fn(() => {
      throw new Error("Provider resolution failed");
    });
    await expect(
      handleChatStream(
        {
          resolveProvider,
          supabase: fakeSupabase("u7"),
        },
        {
          messages: [
            {
              id: "m1",
              parts: [{ text: "hi", type: "text" }],
              role: "user",
            } satisfies UIMessage,
          ],
        }
      )
    ).rejects.toThrow("Provider resolution failed");
  });

  it("onError callback returns user-friendly message", async () => {
    let capturedOnError: ((err: unknown) => string) | undefined;

    mockCreateAgentUIStreamResponse.mockImplementationOnce(
      (opts: { onError?: (err: unknown) => string }) => {
        capturedOnError = opts.onError;
        return Promise.resolve(new Response("ok", { status: 200 }));
      }
    );

    const logger = { error: vi.fn(), info: vi.fn() };

    await handleChatStream(
      {
        logger,
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u8"),
      },
      {
        messages: [
          {
            id: "m1",
            parts: [{ text: "hi", type: "text" }],
            role: "user",
          } satisfies UIMessage,
        ],
      }
    );

    // Test the captured onError callback
    expect(capturedOnError).toBeDefined();
    if (!capturedOnError) {
      throw new Error("onError callback was not captured");
    }
    const errorMsg = capturedOnError(new Error("Test error"));
    expect(errorMsg).toBe("An error occurred while processing your request.");
    expect(logger.error).toHaveBeenCalledWith(
      "chat_stream:error",
      expect.objectContaining({ message: "Test error" })
    );
  });

  it("logs start and finish events", async () => {
    let capturedOnFinish: ((event: unknown) => void) | undefined;

    mockCreateAgentUIStreamResponse.mockImplementationOnce(
      (opts: { onFinish?: (event: unknown) => void }) => {
        capturedOnFinish = opts.onFinish;
        return Promise.resolve(new Response("ok", { status: 200 }));
      }
    );

    const logger = { error: vi.fn(), info: vi.fn() };

    await handleChatStream(
      {
        logger,
        resolveProvider: createResolver("gpt-4o-mini"),
        supabase: fakeSupabase("u9"),
      },
      {
        messages: [
          {
            id: "m1",
            parts: [{ text: "hi", type: "text" }],
            role: "user",
          } satisfies UIMessage,
        ],
      }
    );

    expect(logger.info).toHaveBeenCalledWith(
      "chat_stream:start",
      expect.objectContaining({
        model: "gpt-4o-mini",
        requestId: expect.any(String),
        userId: "u9",
      })
    );

    // Test the captured onFinish callback
    expect(capturedOnFinish).toBeDefined();
    if (!capturedOnFinish) {
      throw new Error("onFinish callback was not captured");
    }
    capturedOnFinish({ finishReason: "stop", usage: { totalTokens: 100 } });
    expect(logger.info).toHaveBeenCalledWith(
      "chat_stream:finish",
      expect.objectContaining({
        finishReason: "stop",
      })
    );
  });
});
