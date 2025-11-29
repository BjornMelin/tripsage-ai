/** @vitest-environment node */

import type { ProviderId } from "@schemas/providers";
import type { LanguageModel, UIMessage } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatDeps, ProviderResolver } from "../_handler";

const streamTextMock = vi.hoisted(() =>
  vi.fn(() => ({
    response: Promise.resolve({ messages: [] as UIMessage[] }),
    toUIMessageStreamResponse: () =>
      new Response(
        new ReadableStream({
          start(controller) {
            controller.close();
          },
        })
      ),
  }))
);

vi.mock("ai", () => ({
  convertToModelMessages: (x: unknown) => x,
  generateObject: vi.fn(),
  NoSuchToolError: class NoSuchToolError extends Error {},
  stepCountIs: () => () => false,
  streamText: streamTextMock,
  tool: vi.fn((config: unknown) => ({
    execute: vi.fn(),
    ...(config as Record<string, unknown>),
  })),
}));

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
      getUser: vi.fn(async () => ({ data: { user: userId ? { id: userId } : null } })),
    },
    from: vi.fn(mockQueryBuilder),
  } as unknown as ChatDeps["supabase"];
}

describe("handleChatStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it("emits usage metadata on finish and persists assistant message (stream stub)", async () => {
    type MessageRow = {
      sessionId: string;
      role: string;
      [key: string]: unknown;
    };
    const memLog: MessageRow[] = [];

    const mockQueryBuilder = (table: string): MockQueryBuilder => {
      if (table === "chat_messages") {
        return {
          eq: vi.fn().mockReturnThis(),
          insert: vi.fn((row: unknown) => {
            memLog.push(row as MessageRow);
            return Promise.resolve({ error: null });
          }),
        };
      }
      if (table === "memories") {
        return {
          eq: vi.fn().mockReturnThis(),
          limit: vi.fn().mockResolvedValue({ data: [] }),
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

    const supabase = {
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u4" } } })) },
      from: vi.fn(mockQueryBuilder),
    } as unknown as ChatDeps["supabase"];

    type MetadataResult = {
      provider?: string;
      [key: string]: unknown;
    };

    let startMeta: MetadataResult | undefined;
    let finishMeta: MetadataResult | undefined;
    const fauxStream = vi.fn(() => ({
      response: Promise.resolve({
        messages: [
          {
            content: [{ text: "hello", type: "text" }],
            id: "assistant-1",
            role: "assistant",
          },
        ],
      }),
      toUIMessageStreamResponse: ({
        messageMetadata,
      }: {
        messageMetadata?: (event: unknown) => MetadataResult | Promise<MetadataResult>;
      }) => {
        startMeta = messageMetadata?.({ part: { type: "start" } }) as MetadataResult;
        finishMeta = messageMetadata?.({
          part: {
            totalUsage: { inputTokens: 45, outputTokens: 78, totalTokens: 123 },
            type: "finish",
          },
        }) as MetadataResult;
        return new Response("ok", { status: 200 });
      },
    }));

    const res = await handleChatStream(
      {
        clock: { now: () => 1000 },
        config: { defaultMaxTokens: 256 },
        logger: { error: vi.fn(), info: vi.fn() },
        resolveProvider: createResolver("gpt-4o-mini"),
        stream: fauxStream as unknown as ChatDeps["stream"],
        supabase,
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
    // assistant message persisted
    expect(memLog.length).toBe(1);
    // Database column uses snake_case
    // biome-ignore lint/style/useNamingConvention: test mirrors DB column name
    expect((memLog[0] as unknown as { session_id: string }).session_id).toBe("s1");
    expect(memLog[0].role).toBe("assistant");
    // provider metadata present in start/finish
    expect(await startMeta).toMatchObject({ provider: "openai" });
    expect(await finishMeta).toMatchObject({ provider: "openai" });
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
              { mediaType: "application/pdf", type: "file", url: "https://x/y.pdf" },
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

  it("400 when clamp leaves no tokens", async () => {
    // Create a huge prompt to trip clamp logic
    const huge = "x".repeat(600_000);
    const res = await handleChatStream(
      {
        config: { defaultMaxTokens: 1024 },
        // Use unknown model to trigger heuristic token counting (fast)
        resolveProvider: createResolver("some-unknown-model"),
        supabase: fakeSupabase("u3"),
      },
      {
        messages: [
          {
            id: "u",
            parts: [{ text: huge, type: "text" }],
            role: "user",
          } satisfies UIMessage,
        ],
      }
    );
    expect(res.status).toBe(400);
    await res.text();
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
    const streamText = vi.fn(() => ({
      toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
    }));
    const res = await handleChatStream(
      {
        resolveProvider,
        stream: streamText as unknown as ChatDeps["stream"],
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
    expect(streamText).toHaveBeenCalledWith(
      expect.objectContaining({
        model: expect.anything(),
      })
    );
  });

  it("calls streamText with correct arguments", async () => {
    const streamText = vi.fn(() => ({
      toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
    }));
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
        stream: streamText as unknown as ChatDeps["stream"],
        supabase: fakeSupabase("u6"),
      },
      {
        desiredMaxTokens: 256,
        messages,
      }
    );
    expect(streamText).toHaveBeenCalledWith(
      expect.objectContaining({
        maxOutputTokens: expect.any(Number),
        messages: expect.anything(),
        model: expect.anything(),
        stopWhen: expect.any(Function),
        system: expect.stringContaining("travel planning assistant"),
        toolChoice: "auto",
        tools: expect.anything(),
      })
    );
    const callArgs = (streamText as ReturnType<typeof vi.fn>).mock.calls[0]?.[0];
    expect(callArgs?.maxOutputTokens).toBeLessThanOrEqual(256);
    expect(callArgs?.system).toBeTruthy();
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

  it("onError returns user-friendly message", async () => {
    const streamText = vi.fn(() => ({
      toUIMessageStreamResponse: ({
        onError,
      }: {
        onError?: (err: unknown) => string;
      }) => {
        const errorMsg = onError?.(new Error("Test error"));
        return new Response(JSON.stringify({ error: errorMsg }), { status: 200 });
      },
    }));
    const res = await handleChatStream(
      {
        logger: { error: vi.fn(), info: vi.fn() },
        resolveProvider: createResolver("gpt-4o-mini"),
        stream: streamText as unknown as ChatDeps["stream"],
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
    const body = await res.json();
    expect(body.error).toBe("An error occurred while processing your request.");
  });
});
