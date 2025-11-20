/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

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
      }),
    },
  })),
}));

// Mock provider registry
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: {} })),
}));

// Mock memory agent
vi.mock("@/lib/agents/memory-agent", () => ({
  runMemoryAgent: vi.fn(() => ({
    toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

describe("/api/agents/memory route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    const res = await mod.POST(req);
    expect(res.status).toBe(200);
  });
});
