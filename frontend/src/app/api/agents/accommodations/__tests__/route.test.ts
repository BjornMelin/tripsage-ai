import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/agents/accommodations route", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("streams when valid and enabled", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
      })),
    }));
    vi.doMock("@/lib/providers/registry", () => ({
      resolveProvider: vi.fn(async () => ({ model: {}, modelId: "gpt-4o" })),
    }));
    vi.doMock("@/lib/agents/accommodation-agent", () => ({
      runAccommodationAgent: vi.fn(() => ({
        toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
      })),
    }));
    vi.doMock("@/lib/ratelimit/config", () => ({
      enforceRouteRateLimit: vi.fn().mockResolvedValue(null),
    }));
    vi.doMock("@/lib/next/route-helpers", () => ({
      errorResponse: vi.fn((opts) =>
        new Response(JSON.stringify({ error: opts.error }), {
          status: opts.status,
        })
      ),
      getTrustedRateLimitIdentifier: vi.fn(() => "hashed-ip"),
      withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
    }));

    const mod = await import("../route");
    const req = new Request("http://localhost/api/agents/accommodations", {
      body: JSON.stringify({
        checkIn: "2025-12-15",
        checkOut: "2025-12-19",
        destination: "NYC",
        guests: 2,
      }),
      method: "POST",
    });
    const res = await mod.POST(req as unknown as import("next/server").NextRequest);
    expect(res.status).toBe(200);
  });

  it("returns 429 when rate limit exceeded", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: async () => ({ data: { user: null } }) },
      })),
    }));
    vi.doMock("@/lib/ratelimit/config", () => ({
      enforceRouteRateLimit: vi.fn().mockResolvedValue({
        error: "rate_limit_exceeded",
        reason: "Too many requests",
        status: 429,
      }),
    }));
    vi.doMock("@/lib/next/route-helpers", () => ({
      errorResponse: vi.fn((opts) =>
        new Response(JSON.stringify({ error: opts.error }), {
          status: opts.status,
        })
      ),
      getTrustedRateLimitIdentifier: vi.fn(() => "hashed-ip"),
    }));

    const mod = await import("../route");
    const req = new Request("http://localhost/api/agents/accommodations", {
      body: JSON.stringify({
        checkIn: "2025-12-15",
        checkOut: "2025-12-19",
        destination: "NYC",
        guests: 2,
      }),
      method: "POST",
    });
    const res = await mod.POST(req as unknown as import("next/server").NextRequest);
    expect(res.status).toBe(429);
    const body = await res.json();
    expect(body.error).toBe("rate_limit_exceeded");
  });
});
