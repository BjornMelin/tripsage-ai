/* @vitest-environment node */
/**
 * @fileoverview Unit tests for handleChatStream function, testing authentication,
 * rate limiting, attachment validation, memory integration, and AI SDK streaming
 * with mocked dependencies and various edge cases.
 */

import { describe, expect, it, vi } from "vitest";
import { handleChatStream } from "../_handler";

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
          select: vi.fn().mockReturnThis(),
          eq: vi.fn().mockReturnThis(),
          order: vi.fn().mockReturnThis(),
          limit: vi
            .fn()
            .mockResolvedValue({ data: memories.map((m) => ({ content: m })) }),
        } as any;
      }
      if (table === "chat_messages") {
        return {
          insert: vi.fn(async () => ({ error: null })),
          select: vi.fn().mockReturnThis(),
          eq: vi.fn().mockReturnThis(),
          order: vi.fn().mockReturnThis(),
          limit: vi.fn().mockReturnThis(),
        } as any;
      }
      if (table === "chat_sessions") {
        return {
          update: vi.fn().mockReturnThis(),
          eq: vi.fn().mockReturnThis(),
        } as any;
      }
      return {} as any;
    }),
  } as any;
}

describe("handleChatStream", () => {
  it("401 when unauthenticated", async () => {
    const res = await handleChatStream(
      {
        supabase: fakeSupabase(null),
        resolveProvider: vi.fn(),
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
            select: vi.fn().mockReturnThis(),
            eq: vi.fn().mockReturnThis(),
            order: vi.fn().mockReturnThis(),
            limit: vi.fn().mockResolvedValue({ data: [] }),
          } as any;
        }
        if (table === "chat_sessions") {
          return {
            update: vi.fn().mockReturnThis(),
            eq: vi.fn().mockReturnThis(),
          } as any;
        }
        return {} as any;
      }),
    } as any;

    const fauxStream = vi.fn(() => ({
      toUIMessageStreamResponse: ({ messageMetadata }: any) => {
        void messageMetadata?.({ part: { type: "start" } });
        void messageMetadata?.({
          part: {
            type: "finish",
            totalUsage: { totalTokens: 123, inputTokens: 45, outputTokens: 78 },
          },
        });
        return new Response("ok", { status: 200 });
      },
    }));

    const res = await handleChatStream(
      {
        supabase,
        resolveProvider: vi.fn(async () => ({
          provider: "openai",
          modelId: "gpt-4o-mini",
          model: {} as any,
        })),
        logger: { info: vi.fn(), error: vi.fn() },
        clock: { now: () => 1000 },
        config: { defaultMaxTokens: 256 },
        stream: fauxStream as any,
      },
      {
        messages: [
          { id: "m", role: "user", parts: [{ type: "text", text: "hello" }] } as any,
        ],
        session_id: "s1",
      }
    );
    expect(res.status).toBe(200);
    // assistant message persisted
    expect(memLog.length).toBe(1);
    expect(memLog[0].session_id).toBe("s1");
    expect(memLog[0].role).toBe("assistant");
  });

  it("429 when rate limited", async () => {
    const res = await handleChatStream(
      {
        supabase: fakeSupabase("u1"),
        resolveProvider: vi.fn(),
        limit: vi.fn(async () => ({ success: false })),
      },
      { messages: [], ip: "1.2.3.4" }
    );
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
  });

  it("400 on invalid attachment type", async () => {
    const res = await handleChatStream(
      {
        supabase: fakeSupabase("u2"),
        resolveProvider: vi.fn(),
      },
      {
        messages: [
          {
            id: "m1",
            role: "user",
            parts: [
              { type: "text", text: "hi" },
              { type: "file", url: "https://x/y.pdf", media_type: "application/pdf" },
            ],
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
        supabase: fakeSupabase("u3"),
        resolveProvider: vi.fn(async () => ({
          provider: "openai",
          modelId: "gpt-4o",
          model: {} as any,
        })),
        config: { defaultMaxTokens: 1024 },
      },
      {
        messages: [
          { id: "u", role: "user", parts: [{ type: "text", text: huge }] } as any,
        ],
      }
    );
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(String(body.error)).toMatch(/No output tokens/);
  });
});
