/** @vitest-environment node */

import { buildTimeoutConfigFromSeconds } from "@ai/timeout";
import type { Agent } from "ai";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

vi.mock("server-only", () => ({}));

const resolveAgentConfigMock = vi.hoisted(() => vi.fn());
const resolveProviderMock = vi.hoisted(() => vi.fn());
const createErrorHandlerMock = vi.hoisted(() => vi.fn(() => "error"));
const consumeStreamMock = vi.hoisted(() => vi.fn());
const captured = vi.hoisted(() => ({ options: null as unknown }));
const createAgentUIStreamResponseMock = vi.hoisted(() =>
  vi.fn((options: unknown) => {
    captured.options = options;
    return new Response("ok", { status: 200 });
  })
);

vi.mock("@/lib/agents/config-resolver", () => ({
  resolveAgentConfig: resolveAgentConfigMock,
}));

vi.mock("@ai/models/registry", () => ({
  resolveProvider: resolveProviderMock,
}));

vi.mock("@/lib/agents/error-recovery", () => ({
  createErrorHandler: createErrorHandlerMock,
}));

vi.mock("@/lib/telemetry/span", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/telemetry/span")>();
  return {
    ...actual,
    withTelemetrySpan: async (
      _name: string,
      _opts: unknown,
      execute: (span: { setAttribute: (key: string, value: string) => void }) => unknown
    ) => execute({ setAttribute: () => undefined }),
  };
});

vi.mock("ai", () => ({
  consumeStream: consumeStreamMock,
  createAgentUIStreamResponse: createAgentUIStreamResponseMock,
}));

describe("createAgentRoute", () => {
  beforeEach(async () => {
    captured.options = null;
    createAgentUIStreamResponseMock.mockClear();
    resolveAgentConfigMock.mockReset();
    resolveProviderMock.mockReset();
    createErrorHandlerMock.mockReset();
    consumeStreamMock.mockClear();

    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );

    setRateLimitFactoryForTests(async () => ({
      limit: 10,
      remaining: 9,
      reset: Date.now() + 60_000,
      success: true,
    }));

    setSupabaseFactoryForTests(async () =>
      unsafeCast({
        auth: {
          getUser: async () => ({ data: { user: { id: "user-1" } }, error: null }),
        },
      })
    );
  });

  afterEach(async () => {
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
  });

  it("passes timeout and message metadata into createAgentUIStreamResponse", async () => {
    resolveAgentConfigMock.mockResolvedValue({
      config: {
        agentType: "memoryAgent",
        createdAt: "2024-01-01T00:00:00.000Z",
        id: "v1700000000_deadbeef",
        model: "gpt-4o",
        parameters: { timeoutSeconds: 42 },
        scope: "global",
        updatedAt: "2024-01-01T00:00:00.000Z",
      },
      versionId: "v1700000000_deadbeef",
    });

    resolveProviderMock.mockResolvedValue({
      model: unsafeCast({}),
      modelId: "gpt-4o",
      provider: "openai",
    });

    const { createAgentRoute } = await import("@/lib/api/factory");

    const handler = createAgentRoute({
      agentFactory: async () => ({
        agent: unsafeCast<Agent>({}),
        defaultMessages: [],
      }),
      agentType: "memoryAgent",
      rateLimit: "agents:memory",
      schema: z.strictObject({ prompt: z.string().min(1) }),
      telemetry: "agents.memory",
    });

    const req = createMockNextRequest({
      body: { prompt: "hello" },
      headers: { authorization: "Bearer test-token" },
      method: "POST",
      url: "http://localhost/api/agents/memory",
    });

    const res = await handler(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const opts = captured.options as {
      messageMetadata?: (options: { part: Record<string, unknown> }) => unknown;
      sendSources?: boolean;
      timeout?: unknown;
    };

    expect(opts.timeout).toEqual(buildTimeoutConfigFromSeconds(42));
    expect(opts.sendSources).toBe(true);

    const usage = { completionTokens: 2, promptTokens: 1, totalTokens: 3 };
    const startMetadata = opts.messageMetadata?.({ part: { type: "start" } }) as {
      agentType?: string;
      modelId?: string;
      requestId?: string;
      versionId?: string;
    };
    expect(startMetadata).toMatchObject({
      agentType: "memoryAgent",
      modelId: "gpt-4o",
      versionId: "v1700000000_deadbeef",
    });
    expect(typeof startMetadata?.requestId).toBe("string");

    const finishMetadata = opts.messageMetadata?.({
      part: { finishReason: "stop", totalUsage: usage, type: "finish" },
    }) as {
      agentType?: string;
      finishReason?: string | null;
      modelId?: string;
      requestId?: string;
      totalUsage?: unknown;
      versionId?: string;
    };
    expect(finishMetadata).toMatchObject({
      agentType: "memoryAgent",
      finishReason: "stop",
      modelId: "gpt-4o",
      totalUsage: usage,
      versionId: "v1700000000_deadbeef",
    });
    expect(typeof finishMetadata?.requestId).toBe("string");
  });
});
