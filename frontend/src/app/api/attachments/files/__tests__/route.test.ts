import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
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

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

// Mock route helpers
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

// Mock global fetch
const MOCK_FETCH = vi.fn();
(globalThis as { fetch: typeof fetch }).fetch = MOCK_FETCH;

describe("/api/attachments/files", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MOCK_FETCH.mockResolvedValue(
      new Response(
        JSON.stringify({
          files: [{ filename: "test.pdf", id: "1" }],
          limit: 50,
          offset: 0,
          total: 1,
        }),
        { status: 200 }
      )
    );
  });

  it("forwards Authorization and sets next tags", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      headers: { authorization: "Bearer token" },
      method: "GET",
      url: "http://localhost/api/attachments/files?limit=10&offset=0",
    });

    const res = await mod.GET(req);
    expect(res.status).toBe(200);
    expect(MOCK_FETCH).toHaveBeenCalledTimes(1);
    const [calledUrl, options] = MOCK_FETCH.mock.calls[0] as [
      string,
      RequestInit & { next?: { tags: string[] } },
    ];
    expect(calledUrl).toContain("/api/attachments/files?limit=10&offset=0");
    expect(options?.method).toBe("GET");
    expect(options?.headers).toMatchObject({ authorization: "Bearer token" });
    expect(options?.next?.tags).toContain("attachments");
  });
});
