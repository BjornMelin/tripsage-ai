/* @vitest-environment node */
/**
 * @fileoverview Unit tests for handleChatNonStream: auth, attachments, clamping
 * and usage mapping, with injected dependencies and mocked AI SDK.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

let handleChatNonStream: (deps: any, payload: any) => Promise<Response>;

/**
 * Creates a mock Supabase client for testing handleChatNonStream functionality.
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
        } as any;
      }
      return {} as any;
    }),
  } as any;
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
      { supabase: fakeSupabase(null), resolveProvider: vi.fn() },
      { messages: [] }
    );
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.error).toBe("unauthorized");
  });

  it("400 on invalid attachment type", async () => {
    const res = await handleChatNonStream(
      { supabase: fakeSupabase("u2"), resolveProvider: vi.fn() },
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
    const huge = "x".repeat(600_000);
    const res = await handleChatNonStream(
      {
        supabase: fakeSupabase("u3"),
        resolveProvider: vi.fn(async () => ({
          provider: "openai",
          modelId: "some-unknown-model",
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
    await res.text();
  });

  it("200 with content and usage mapping", async () => {
    const supabase = fakeSupabase("u4");
    const generateText = vi.fn(async () => ({
      text: "Hello world",
      usage: { totalTokens: 42, promptTokens: 10, completionTokens: 32 },
    }));
    const res = await handleChatNonStream(
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
        generate: generateText as any,
      },
      {
        messages: [
          { id: "u1", role: "user", parts: [{ type: "text", text: "hi" }] } as any,
        ],
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
