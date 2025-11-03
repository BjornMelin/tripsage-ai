/* @vitest-environment node */
/**
 * @fileoverview Unit tests for handleChatStream function, testing authentication,
 * rate limiting, attachment validation, memory integration, and AI SDK streaming
 * with mocked dependencies and various edge cases.
 */

import type { LanguageModel, UIMessage } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatDeps, ChatPayload } from "../_handler";

let handleChatStream: (deps: ChatDeps, payload: ChatPayload) => Promise<Response>;

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
  beforeEach(async () => {
    vi.resetModules();
    vi.doMock("ai", () => ({
      convertToModelMessages: (x: unknown) => x,
      streamText: vi.fn(),
    }));
    ({ handleChatStream } = await import("../_handler"));
  });
  it("401 when unauthenticated", async () => {
    const res = await handleChatStream(
      {
        resolveProvider: vi.fn(),
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
      // biome-ignore lint/style/useNamingConvention: API field uses snake_case
      session_id: string;
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
      // biome-ignore lint/style/useNamingConvention: AI SDK method name
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
        resolveProvider: vi.fn(async () => ({
          model: {} as LanguageModel,
          modelId: "gpt-4o-mini",
          provider: "openai",
        })),
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
        // biome-ignore lint/style/useNamingConvention: API field uses snake_case
        session_id: "s1",
      }
    );
    expect(res.status).toBe(200);
    // assistant message persisted
    expect(memLog.length).toBe(1);
    expect(memLog[0].session_id).toBe("s1");
    expect(memLog[0].role).toBe("assistant");
    // provider metadata present in start/finish
    expect(await startMeta).toMatchObject({ provider: "openai" });
    expect(await finishMeta).toMatchObject({ provider: "openai" });
  });

  it("429 when rate limited", async () => {
    const res = await handleChatStream(
      {
        limit: vi.fn(async () => ({ success: false })),
        resolveProvider: vi.fn(),
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
        resolveProvider: vi.fn(),
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
        resolveProvider: vi.fn(async () => ({
          model: {} as LanguageModel,
          modelId: "some-unknown-model",
          provider: "openai",
        })),
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
});
