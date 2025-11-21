/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  apiRouteSupabaseMock,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/api-route-helpers";

function createMockRequest(url: string): NextRequest {
  return new NextRequest(new Request(url));
}

describe("/api/dashboard route", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
  });

  it("returns default metrics when no logs are present", async () => {
    const selectMock = vi.fn().mockResolvedValue({ data: [], error: null });
    apiRouteSupabaseMock.from.mockReturnValue({ select: selectMock } as never);
    const mod = await import("../route");
    const req = createMockRequest("http://localhost/api/dashboard");
    const res = await mod.GET(req, { params: Promise.resolve({}) });

    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      avgLatencyMs: number;
      errorRate: number;
      totalRequests: number;
    };
    expect(body.totalRequests).toBe(0);
    expect(body.errorRate).toBe(0);
    expect(body.avgLatencyMs).toBe(0);
    expect(selectMock).toHaveBeenCalledWith("id, status, created_at");
  });
});
