import { describe, expect, it, vi } from "vitest";
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
vi.mock("@/lib/providers/registry", () => ({
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

describe("/api/agents/memory validation", () => {
  it("returns 400 on invalid body", async () => {
    const mod = await import("../route");
    // Missing required fields like records
    const req = createMockNextRequest({
      body: {},
      method: "POST",
      url: "http://localhost/api/agents/memory",
    });
    const res = await mod.POST(req);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe("invalid_request");
    expect(Array.isArray(data.issues)).toBe(true);
  });
});
