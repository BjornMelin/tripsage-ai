/** @vitest-environment node */

import type { ProviderResolution } from "@schemas/providers";
import type { LanguageModel, UIMessage } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { createMockSupabaseClient } from "@/test/mocks/supabase";
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
    if (!Array.isArray(params.uiMessages)) {
      throw new Error("createAgentUIStreamResponse requires uiMessages array");
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
  secureUuid: vi.fn(() => "test-uuid-123"),
}));

const MOCK_RESOLVE_PROVIDER = vi.hoisted(() =>
  vi.fn(
    async (): Promise<ProviderResolution> => ({
      model: unsafeCast<LanguageModel>({ id: "gpt-4o-mini", providerId: "openai" }),
      modelId: "gpt-4o-mini",
      provider: "openai" as const,
    })
  )
);

const makeSupabase = (): TypedServerSupabase =>
  createMockSupabaseClient({ user: { id: "user-1" } });

describe("/api/chat/stream route smoke", () => {
  const createDeps = (overrides?: Partial<ChatDeps>): ChatDeps => ({
    clock: { now: () => 0 },
    config: { defaultMaxTokens: 1024 },
    logger: {
      error: vi.fn(),
      info: vi.fn(),
    },
    resolveProvider: MOCK_RESOLVE_PROVIDER,
    supabase: makeSupabase(),
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("resolves provider using the injected userId", async () => {
    const deps = createDeps();

    await handleChatStream(deps, {
      ip: "1.2.3.4",
      messages: [],
      userId: "user-1",
    });

    expect(deps.resolveProvider).toHaveBeenCalledWith("user-1", undefined);
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
      userId: "user-1",
    };

    const res = await handleChatStream(deps, payload);
    expect(res.status).toBe(200);
  });
});
