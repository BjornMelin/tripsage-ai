import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/agents/memory route", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("streams when valid and enabled", async () => {
    vi.doMock("@/lib/supabase", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
      })),
    }));
    vi.doMock("@/lib/providers/registry", () => ({
      resolveProvider: vi.fn(async () => ({ model: {} })),
    }));
    vi.doMock("@/lib/agents/memory-agent", () => ({
      runMemoryAgent: vi.fn(() => ({
        toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
      })),
    }));

    const mod = await import("../route");
    const req = new Request("http://localhost/api/agents/memory", {
      body: JSON.stringify({
        records: [
          {
            category: "user_preference",
            content: "User prefers window seats",
          },
        ],
      }),
      method: "POST",
    });
    const res = await mod.POST(req as unknown as import("next/server").NextRequest);
    expect(res.status).toBe(200);
  });
});
