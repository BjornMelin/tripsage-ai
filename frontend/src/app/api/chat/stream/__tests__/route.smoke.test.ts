/** @vitest-environment node */

import type { ProviderResolution } from "@schemas/providers";
import type { UIMessage } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatDeps } from "../_handler";
import { handleChatStream } from "../_handler";

const MOCK_SUPABASE = vi.hoisted(
  () =>
    ({
      auth: {
        getUser: vi.fn(async () => ({
          data: { user: { id: "user-1" } },
          error: null,
        })),
      },
    }) as never
);

const MOCK_RESOLVE_PROVIDER = vi.hoisted(() =>
  vi.fn(
    async (): Promise<ProviderResolution> => ({
      model: {
        id: "gpt-4o-mini",
        providerId: "openai",
      } as never,
      modelId: "gpt-4o-mini",
      provider: "openai" as const,
    })
  )
);

const MOCK_RATE_LIMITER = vi.hoisted(() =>
  vi.fn(async () => ({
    limit: 40,
    remaining: 39,
    reset: Date.now() + 60_000,
    success: true,
  }))
);

describe("/api/chat/stream route smoke", () => {
  const createDeps = (overrides?: Partial<ChatDeps>): ChatDeps => ({
    clock: { now: () => Date.now() },
    config: { defaultMaxTokens: 1024 },
    limit: MOCK_RATE_LIMITER,
    logger: {
      error: vi.fn(),
      info: vi.fn(),
    },
    resolveProvider: MOCK_RESOLVE_PROVIDER,
    supabase: MOCK_SUPABASE,
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

    const res = await handleChatStream(deps, { ip: "1.2.3.4", messages: [] });
    expect(res.status).toBe(401);
  });

  it("returns 429 when rate limited", async () => {
    const deps = createDeps({
      limit: vi.fn(async () => ({
        limit: 40,
        remaining: 0,
        reset: Date.now() + 60_000,
        success: false,
      })),
    });

    const res = await handleChatStream(deps, { ip: "1.2.3.4", messages: [] });
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
