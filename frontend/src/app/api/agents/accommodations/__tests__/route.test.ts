import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/agents/accommodations route", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  // Feature flags removed: route is always enabled

  it("streams when valid and enabled", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
      })),
    }));
    vi.doMock("@/lib/providers/registry", () => ({
      resolveProvider: vi.fn(async () => ({ model: {} })),
    }));
    vi.doMock("@/lib/agents/accommodation-agent", () => ({
      runAccommodationAgent: vi.fn(() => ({
        toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
      })),
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
});
