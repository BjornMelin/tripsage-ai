/* @vitest-environment node */
/**
 * @fileoverview Unit tests for handleChatStream function, testing authentication,
 * rate limiting, attachment validation, memory integration, and AI SDK streaming
 * with mocked dependencies and various edge cases.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

let handleChatStream: (deps: any, payload: any) => Promise<Response>;

/**
 * Creates a mock Supabase client for testing handleChatStream functionality.
 *
 * @param userId - User ID for authentication mocking, or null for unauthenticated.
 * @param memories - Array of memory content strings for memory hydration testing.
 * @returns Mock Supabase client with basic database operations.
 */
function fakeSupabase(userId: string | null, memories: string[] = []) {
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
        } as any;
      }
      if (table === "chat_messages") {
        return {
          eq: vi.fn().mockReturnThis(),
          insert: vi.fn(async () => ({ error: null })),
          limit: vi.fn().mockReturnThis(),
          order: vi.fn().mockReturnThis(),
          select: vi.fn().mockReturnThis(),
        } as any;
      }
      if (table === "chat_sessions") {
        return {
          eq: vi.fn().mockReturnThis(),
          update: vi.fn().mockReturnThis(),
        } as any;
      }
      return {} as any;
    }),
  } as any;
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
    const memLog: any[] = [];
    const supabase = {
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u4" } } })) },
      from: vi.fn((table: string) => {
        if (table === "chat_messages") {
          return {
            insert: vi.fn(async (row: any) => {
              memLog.push(row);
              return { error: null };
            }),
          } as any;
        }
        if (table === "memories") {
          return {
            eq: vi.fn().mockReturnThis(),
            limit: vi.fn().mockResolvedValue({ data: [] }),
            order: vi.fn().mockReturnThis(),
            select: vi.fn().mockReturnThis(),
          } as any;
        }
        if (table === "chat_sessions") {
          return {
            eq: vi.fn().mockReturnThis(),
            update: vi.fn().mockReturnThis(),
          } as any;
        }
        return {} as any;
      }),
    } as any;

    let startMeta: any | undefined;
    let finishMeta: any | undefined;
    const fauxStream = vi.fn(() => ({
      toUIMessageStreamResponse: ({ messageMetadata }: any) => {
        startMeta = messageMetadata?.({ part: { type: "start" } });
        finishMeta = messageMetadata?.({
          part: {
            totalUsage: { inputTokens: 45, outputTokens: 78, totalTokens: 123 },
            type: "finish",
          },
        });
        return new Response("ok", { status: 200 });
      },
    }));

    const res = await handleChatStream(
      {
        clock: { now: () => 1000 },
        config: { defaultMaxTokens: 256 },
        logger: { error: vi.fn(), info: vi.fn() },
        resolveProvider: vi.fn(async () => ({
          model: {} as any,
          modelId: "gpt-4o-mini",
          provider: "openai",
        })),
        stream: fauxStream as any,
        supabase,
      },
      {
        messages: [
          { id: "m", parts: [{ text: "hello", type: "text" }], role: "user" } as any,
        ],
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
              { media_type: "application/pdf", type: "file", url: "https://x/y.pdf" },
            ],
            role: "user",
          } as any,
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
          model: {} as any,
          modelId: "some-unknown-model",
          provider: "openai",
        })),
        supabase: fakeSupabase("u3"),
      },
      {
        messages: [
          { id: "u", parts: [{ text: huge, type: "text" }], role: "user" } as any,
        ],
      }
    );
    expect(res.status).toBe(400);
    await res.text();
  });
});
