/** @vitest-environment node */

import type { ProviderResolution } from "@schemas/providers";
import type { User } from "@supabase/supabase-js";
import type { LanguageModel, UIMessage } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import type { ChatDeps } from "../_handler";
import { handleChatStream } from "../_handler";

// Mock the chat agent module
vi.mock("@ai/agents", () => ({
  CHAT_DEFAULT_SYSTEM_PROMPT: "test-system-prompt",
  createChatAgent: vi.fn(() => ({
    agent: {
      generate: vi.fn(),
      stream: vi.fn(),
    },
    modelId: "gpt-4o-mini",
  })),
  validateChatMessages: vi.fn(() => ({ valid: true })),
}));

// Mock createAgentUIStreamResponse with parameter validation
vi.mock("ai", () => ({
  createAgentUIStreamResponse: vi.fn((params) => {
    // Validate mock parameters before returning Response
    if (!params || typeof params !== "object") {
      throw new Error("createAgentUIStreamResponse requires a parameters object");
    }
    if (!params.agent) {
      throw new Error("createAgentUIStreamResponse requires an agent");
    }
    if (!Array.isArray(params.messages)) {
      throw new Error("createAgentUIStreamResponse requires messages array");
    }
    return new Response("ok", { status: 200 });
  }),
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

const MOCK_SUPABASE = vi.hoisted(() => {
  const mockUser = { id: "user-1" } as unknown as User;

  return {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: mockUser },
        error: null,
      })),
    },
  } as unknown as TypedServerSupabase;
});

const MOCK_RESOLVE_PROVIDER = vi.hoisted(() =>
  vi.fn(
    async (): Promise<ProviderResolution> => ({
      model: {
        id: "gpt-4o-mini",
        providerId: "openai",
      } as unknown as LanguageModel,
      modelId: "gpt-4o-mini",
      provider: "openai" as const,
    })
  )
);

const MOCK_RATE_LIMITER = vi.hoisted(() =>
  vi.fn(async () => ({
    limit: 40,
    remaining: 39,
    reset: 60_000,
    success: true,
  }))
);

describe("/api/chat/stream route smoke", () => {
  const createDeps = (overrides?: Partial<ChatDeps>): ChatDeps => ({
    clock: { now: () => 0 },
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
      } as unknown as TypedServerSupabase,
    });

    const res = await handleChatStream(deps, { ip: "1.2.3.4", messages: [] });
    expect(res.status).toBe(401);
  });

  it("returns 429 when rate limited", async () => {
    const deps = createDeps({
      limit: vi.fn(async () => ({
        limit: 40,
        remaining: 0,
        reset: 60_000,
        success: false,
      })),
    });

    const res = await handleChatStream(deps, { ip: "1.2.3.4", messages: [] });
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
  });

  it("returns 200 on success with mocked agent", async () => {
    const deps = createDeps();

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
