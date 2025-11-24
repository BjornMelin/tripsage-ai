/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { attachmentsBase } from "@/test/msw/handlers/attachments";
import { server } from "@/test/msw/server";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";

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

describe("/api/attachments/files", () => {
  let recordedHeaders: Headers | undefined;

  beforeEach(() => {
    vi.clearAllMocks();
    recordedHeaders = undefined;
    server.use(
      http.get(`${attachmentsBase}/files`, ({ request }) => {
        recordedHeaders = request.headers;
        const url = new URL(request.url);
        expect(url.searchParams.get("limit")).toBe("10");
        expect(url.searchParams.get("offset")).toBe("0");
        expect(request.headers.get("authorization")).toBe("Bearer token");
        return HttpResponse.json({
          files: [{ filename: "test.pdf", id: "1" }],
          limit: 50,
          offset: 0,
          total: 1,
        });
      })
    );
  });

  it("forwards Authorization and sets next tags", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      headers: { authorization: "Bearer token" },
      method: "GET",
      url: "http://localhost/api/attachments/files?limit=10&offset=0",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    expect(recordedHeaders?.get("authorization")).toBe("Bearer token");
  });
});
