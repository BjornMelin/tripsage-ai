/**
 * @vitest-environment node
 */

import type { UIMessage } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProviderResolution } from "@/lib/providers/types";
import type { ChatDeps } from "../_handler";
import { handleChatStream } from "../_handler";

describe("/api/chat/stream route smoke", () => {
  const mockSupabase = {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: { id: "user-1" } },
        error: null,
      })),
    },
  } as never;

  const mockResolveProvider = vi.fn(
    async (): Promise<ProviderResolution> => ({
      model: {} as never,
      modelId: "gpt-4o-mini",
      provider: "openai" as const,
    })
  );

  const mockRateLimiter = vi.fn(async () => ({
    limit: 40,
    remaining: 39,
    reset: Date.now() + 60000,
    success: true,
  }));

  const createDeps = (overrides?: Partial<ChatDeps>): ChatDeps => ({
    clock: { now: () => Date.now() },
    config: { defaultMaxTokens: 1024 },
    limit: mockRateLimiter,
    logger: {
      error: vi.fn(),
      info: vi.fn(),
    },
    resolveProvider: mockResolveProvider,
    supabase: mockSupabase,
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns 401 unauthenticated", async () => {
    const deps = createDeps({
      supabase: {
        auth: {
          getUser: vi.fn(async () => ({
            data: { user: null },
            error: { message: "Unauthorized" },
          })),
        },
      } as never,
    });

    const payload = {
      ip: "1.2.3.4",
      messages: [],
    };

    const res = await handleChatStream(deps, payload);
    expect(res.status).toBe(401);
  });

  it("returns 429 when rate limited", async () => {
    const deps = createDeps({
      limit: vi.fn(async () => ({
        limit: 40,
        remaining: 0,
        reset: Date.now() + 60000,
        success: false,
      })),
    });

    const payload = {
      ip: "1.2.3.4",
      messages: [],
    };

    const res = await handleChatStream(deps, payload);
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
  });

  it("returns 200 on success with mocked provider and stream", async () => {
    const mockStream = vi.fn(() => ({
      toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
    }));

    const deps = createDeps({
      stream: mockStream as never,
    });

    const payload = {
      ip: "1.2.3.4",
      messages: [
        {
          id: "1",
          parts: [{ text: "hi", type: "text" }],
          role: "user" as const,
        },
      ] as UIMessage[],
    };

    const res = await handleChatStream(deps, payload);
    expect(res.status).toBe(200);
  });
});
