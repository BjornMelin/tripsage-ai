import { describe, expect, it, vi } from "vitest";

describe("/api/agents/flights validation", () => {
  it("returns 400 on invalid body", async () => {
    vi.doMock("@/lib/supabase", () => ({
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
    // Missing required fields like origin/destination/departureDate
    const req = new Request("http://localhost/api/agents/flights", {
      body: JSON.stringify({ passengers: 1 }),
      method: "POST",
    });
    const res = await mod.POST(req as unknown as import("next/server").NextRequest);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe("invalid_request");
    expect(typeof data.reason).toBe("string");
  });
});
