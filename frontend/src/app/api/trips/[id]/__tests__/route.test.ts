/** @vitest-environment node */

import type { TripsRow } from "@schemas/supabase";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setSupabaseFactoryForTests } from "@/lib/api/factory";
import { stubRateLimitDisabled, unstubAllEnvs } from "@/test/env-helpers";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";
import { setupUpstashMocks } from "@/test/setup/upstash";
import { DELETE, GET, PUT } from "../route";

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(
      getMockCookiesForTest({
        "sb-access-token": "test-token",
      })
    )
  ),
}));

const baseRow: TripsRow = {
  budget: 5000,
  created_at: "2024-01-01T00:00:00.000Z",
  currency: "USD",
  destination: "Paris",
  end_date: "2024-01-10T00:00:00.000Z",
  flexibility: {},
  id: 1,
  name: "Test Trip",
  notes: ["note"],
  search_metadata: {},
  start_date: "2024-01-05T00:00:00.000Z",
  status: "planning",
  travelers: 2,
  trip_type: "leisure",
  updated_at: "2024-01-02T00:00:00.000Z",
  user_id: "11111111-1111-4111-8aaa-111111111111",
};

const { redis, ratelimit } = setupUpstashMocks();

function createSupabaseMock(rowOverride?: Partial<TripsRow>) {
  const row: TripsRow = { ...baseRow, ...(rowOverride ?? {}) };
  const builder = {
    delete() {
      this.operation = "delete";
      return this;
    },
    eq() {
      return this;
    },
    error: null as unknown,
    operation: "select" as "select" | "update" | "delete",
    select() {
      if (this.operation !== "update") {
        this.operation = "select";
      }
      return this;
    },
    single: vi.fn(() => {
      if (builder.operation === "select") return { data: row, error: null };
      if (builder.operation === "update")
        return { data: { ...row, ...builder.updatePayload }, error: null };
      return { data: null, error: null };
    }),
    update(payload: Record<string, unknown>) {
      this.operation = "update";
      this.updatePayload = payload;
      return this;
    },
    updatePayload: {} as Record<string, unknown>,
  };

  return {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: { id: row.user_id } },
        error: null,
      })),
    },
    from: vi.fn(() => builder),
  };
}

describe("/api/trips/[id]", () => {
  beforeEach(() => {
    redis.__reset?.();
    ratelimit.__reset?.();
    stubRateLimitDisabled();
  });

  afterEach(() => {
    setSupabaseFactoryForTests(null);
    unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("returns 400 for invalid trip id", async () => {
    const mockSupabase = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/abc",
    });
    const res = await GET(req, createRouteParamsContext({ id: "abc" }));

    expect(res.status).toBe(400);
  });

  it("fetches a trip for the authenticated user", async () => {
    const mockSupabase = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/1",
    });
    const res = await GET(req, createRouteParamsContext({ id: "1" }));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.title).toBe(baseRow.name);
    expect(mockSupabase.from).toHaveBeenCalledWith("trips");
  });

  it("updates a trip with validated payload", async () => {
    const mockSupabase = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      body: { destination: "Rome", title: "Updated Trip" },
      method: "PUT",
      url: "http://localhost/api/trips/1",
    });
    const res = await PUT(req, createRouteParamsContext({ id: "1" }));
    const json = await res.json();
    if (res.status >= 400) {
      console.error("PUT response", res.status, json);
    }
    expect(res.status).toBe(200);
    expect(json.destination).toBe("Rome");
    expect(json.title).toBe("Updated Trip");
  });

  it("deletes a trip and returns 204", async () => {
    const mockSupabase = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/trips/1",
    });
    const res = await DELETE(req, createRouteParamsContext({ id: "1" }));
    if (res.status >= 400) {
      const json = await res.json();
      console.error("DELETE response", res.status, json);
    }

    expect(res.status).toBe(204);
  });
});
