import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/agents/flights route", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env.AGENT_WAVE_FLIGHT = "true";
  });

  it("returns 503 when feature flag disabled", async () => {
    process.env.AGENT_WAVE_FLIGHT = "false";
    const mod = await import("../route");
    const req = new Request("http://localhost/api/agents/flights", {
      body: JSON.stringify({
        departureDate: "2025-12-15",
        destination: "JFK",
        origin: "SFO",
        passengers: 1,
      }),
      method: "POST",
    });
    const res = await mod.POST(req as unknown as import("next/server").NextRequest);
    expect(res.status).toBe(503);
  });

  it("streams when valid and enabled", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
      })),
    }));
    vi.doMock("@/lib/providers/registry", () => ({
      resolveProvider: vi.fn(async () => ({ model: {} })),
    }));
    vi.doMock("@/lib/agents/flight-agent", () => ({
      runFlightAgent: vi.fn(() => ({
        toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
      })),
    }));

    const mod = await import("../route");
    const req = new Request("http://localhost/api/agents/flights", {
      body: JSON.stringify({
        departureDate: "2025-12-15",
        destination: "JFK",
        origin: "SFO",
        passengers: 1,
      }),
      method: "POST",
    });
    const res = await mod.POST(req as unknown as import("next/server").NextRequest);
    expect(res.status).toBe(200);
  });
});
