/** @vitest-environment node */

import { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";
import { GET as getDashboard } from "../route";

function createMockRequest(url: string): NextRequest {
  return new NextRequest(new Request(url));
}

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(() => ({
    from: vi.fn(() => ({
      gte: vi.fn().mockReturnThis(),
      limit: vi.fn().mockResolvedValue({ data: [], error: null }),
      lte: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
    })),
  })),
}));

describe("/api/dashboard route", () => {
  it("returns default metrics when no logs are present", async () => {
    const req = createMockRequest("http://localhost/api/dashboard");
    const res = await getDashboard(req as never, { supabase: {} as never } as never);

    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      avgLatencyMs: number;
      errorRate: number;
      totalRequests: number;
    };
    expect(body.totalRequests).toBe(0);
    expect(body.errorRate).toBe(0);
    expect(body.avgLatencyMs).toBe(0);
  });
});
