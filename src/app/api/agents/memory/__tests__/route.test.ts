/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import { TEST_USER_ID } from "@/test/helpers/ids";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";

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
        data: { user: { id: TEST_USER_ID } },
      }),
    },
  })),
}));

// Mock provider registry
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: {} })),
}));

// Mock memory agent
vi.mock("@ai/agents/memory-agent", () => ({
  runMemoryAgent: vi.fn(() => ({
    toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

describe("/api/agents/memory route", () => {
  const supabaseClient = {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: { id: TEST_USER_ID } },
        error: null,
      })),
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    setRateLimitFactoryForTests(async () => ({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60000,
      success: true,
    }));
    setSupabaseFactoryForTests(async () => supabaseClient as never);
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: { id: TEST_USER_ID } },
      error: null,
    });
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
  });

  it("streams when valid and enabled", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: {
        records: [
          {
            category: "user_preference",
            content: "User prefers window seats",
          },
        ],
      },
      method: "POST",
      url: "http://localhost/api/agents/memory",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
  });
});
