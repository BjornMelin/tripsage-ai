/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { setRateLimitFactoryForTests } from "@/lib/api/factory";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";

vi.mock("@/lib/agents/config-resolver", () => ({
  resolveAgentConfig: vi.fn(async () => ({ config: { model: "gpt-4o-mini" } })),
}));

// Mock next/headers cookies() before any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
        error: null,
      }),
    },
  })),
}));

// Mock provider registry
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: {} })),
}));

// Mock budget agent
vi.mock("@ai/agents", () => ({
  createBudgetAgent: vi.fn(() => ({
    agent: {},
    agentType: "budgetPlanning",
    defaultMessages: [{ content: "schema", role: "user" }],
    modelId: "gpt-4o",
  })),
}));

// Mock createAgentUIStreamResponse with streaming Response
const mockCreateAgentUIStreamResponse = vi.fn(() => {
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode("data: test\n\n"));
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "Content-Type": "text/event-stream" },
    status: 200,
  });
});
vi.mock("ai", () => ({
  createAgentUIStreamResponse: mockCreateAgentUIStreamResponse,
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

const mockLimitFn = vi.hoisted(() => vi.fn());

describe("/api/agents/budget route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setRateLimitFactoryForTests(
      async () =>
        (await mockLimitFn()) ?? {
          limit: 30,
          remaining: 29,
          reset: Date.now() + 60_000,
          success: true,
        }
    );
    mockLimitFn.mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60_000,
      success: true,
    });
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
  });

  it("streams when valid and enabled", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: {
        destination: "Tokyo",
        durationDays: 7,
        travelers: 2,
      },
      method: "POST",
      url: "http://localhost/api/agents/budget",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    expect(mockCreateAgentUIStreamResponse).toHaveBeenCalledTimes(1);

    // Assert that createAgentUIStreamResponse was called with expected structure
    expect(mockCreateAgentUIStreamResponse).toHaveBeenCalledWith(
      expect.objectContaining({
        agent: expect.any(Object),
        messages: expect.any(Array),
      })
    );
  });
});
