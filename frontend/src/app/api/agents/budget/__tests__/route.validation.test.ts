import { describe, expect, it, vi } from "vitest";

describe("/api/agents/budget validation", () => {
  it("returns 400 on invalid body", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
      })),
    }));
    vi.doMock("@/lib/providers/registry", () => ({
      resolveProvider: vi.fn(async () => ({ model: {} })),
    }));
    vi.doMock("@/lib/agents/budget-agent", () => ({
      runBudgetAgent: vi.fn(() => ({
        toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
      })),
    }));

    const mod = await import("../route");
    // Missing required fields like destination/durationDays
    const req = new Request("http://localhost/api/agents/budget", {
      body: JSON.stringify({ travelers: 2 }),
      method: "POST",
    });
    const res = await mod.POST(req as unknown as import("next/server").NextRequest);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe("invalid_request");
    expect(Array.isArray(data.issues)).toBe(true);
  });
});
