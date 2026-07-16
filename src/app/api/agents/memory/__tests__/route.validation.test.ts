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
import { createMockSupabaseClient } from "@/test/mocks/supabase";

vi.mock("ai", () => ({
  consumeStream: vi.fn(),
  createUIMessageStreamResponse: vi.fn(),
  toUIMessageStream: vi.fn(),
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
  resolveProvider: vi.fn(async () => ({ model: {}, modelId: "openai/gpt-5.5" })),
}));

// Mock memory agent
vi.mock("@ai/agents/memory-agent", () => ({
  runMemoryAgent: vi.fn(() => ({ stream: new ReadableStream() })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

describe("/api/agents/memory validation", () => {
  beforeEach(() => {
    const mockLimitFn = vi.fn().mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60000,
      success: true,
    });
    setRateLimitFactoryForTests(async () => mockLimitFn());
    setSupabaseFactoryForTests(async () =>
      createMockSupabaseClient({ user: { id: TEST_USER_ID } })
    );
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
  });

  it("returns 400 on invalid body", async () => {
    const mod = await import("../route");
    // Missing required fields like records
    const req = createMockNextRequest({
      body: {},
      method: "POST",
      url: "http://localhost/api/agents/memory",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe("invalid_request");
    expect(Array.isArray(data.issues)).toBe(true);
  }, 20_000);
});
