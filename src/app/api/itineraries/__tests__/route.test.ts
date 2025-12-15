/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setSupabaseFactoryForTests } from "@/lib/api/factory";
import type { Database } from "@/lib/supabase/database.types";
import { stubRateLimitDisabled, unstubAllEnvs } from "@/test/helpers/env";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";
import { setupUpstashMocks } from "@/test/upstash/redis-mock";
import { GET, POST } from "../route";

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(
      getMockCookiesForTest({
        "sb-access-token": "test-token",
      })
    )
  ),
}));

type ItineraryItemsRow = Database["public"]["Tables"]["itinerary_items"]["Row"];

const baseItem: ItineraryItemsRow = {
  booking_status: "planned",
  created_at: "2024-01-01T00:00:00.000Z",
  currency: "USD",
  description: null,
  end_time: null,
  external_id: null,
  id: 1,
  item_type: "activity",
  location: null,
  metadata: null,
  price: 100,
  start_time: "2024-01-05T12:00:00.000Z",
  title: "Museum",
  trip_id: 123,
  updated_at: "2024-01-01T00:00:00.000Z",
  user_id: "11111111-1111-4111-8aaa-111111111111",
};

const { redis, ratelimit } = setupUpstashMocks();

type SupabaseMockOptions = {
  getUserId?: string;
  insertResult?: { data: ItineraryItemsRow | null; error: unknown | null };
  listResult?: { data: ItineraryItemsRow[] | null; error: unknown | null };
  tripSingleResult?: {
    data: { id: number } | null;
    error: { code?: string; message?: string } | null;
  };
};

function createSupabaseMock(opts: SupabaseMockOptions = {}) {
  const listResult = opts.listResult ?? { data: [baseItem], error: null };
  const insertResult = opts.insertResult ?? { data: baseItem, error: null };
  const tripSingleResult = opts.tripSingleResult ?? {
    data: { id: baseItem.trip_id },
    error: null,
  };
  const builders: Array<{
    table: string;
    eqCalls: Array<[string, unknown]>;
    insertPayload: unknown;
    orderCalls: Array<[string, unknown]>;
  }> = [];

  const from = vi.fn((table: string) => {
    const state = {
      eqCalls: [] as Array<[string, unknown]>,
      insertPayload: null as unknown,
      operation: "select" as "select" | "insert" | "list",
      orderCalls: [] as Array<[string, unknown]>,
      table,
    };
    builders.push(state);

    const builder = {
      eq: vi.fn((column: string, value: unknown) => {
        state.eqCalls.push([column, value]);
        return builder;
      }),
      insert: vi.fn((payload: unknown) => {
        state.operation = "insert";
        state.insertPayload = payload;
        return builder;
      }),
      order: vi.fn((column: string, options?: unknown) => {
        state.operation = "list";
        state.orderCalls.push([column, options]);
        return builder;
      }),
      select: vi.fn(() => builder),
      single: vi.fn(() => {
        if (table === "trips") {
          return tripSingleResult;
        }
        if (table === "itinerary_items" && state.operation === "insert") {
          return insertResult;
        }
        return { data: null, error: null };
      }),
      // biome-ignore lint/suspicious/noThenProperty: Mock promise-like object for testing
      then(
        onFulfilled: (value: {
          data: ItineraryItemsRow[] | null;
          error: unknown | null;
        }) => unknown
      ) {
        if (table === "itinerary_items" && state.operation !== "insert") {
          return Promise.resolve(listResult).then(onFulfilled);
        }
        return Promise.resolve({ data: null, error: null }).then(onFulfilled);
      },
    };

    return builder;
  });

  const userId = opts.getUserId ?? baseItem.user_id;

  return {
    builders,
    client: {
      auth: {
        getUser: vi.fn(async () => ({ data: { user: { id: userId } }, error: null })),
      },
      from,
    },
  };
}

describe("/api/itineraries", () => {
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

  it("lists itinerary items scoped to the authenticated user", async () => {
    const mock = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mock.client as never));

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/itineraries",
    });
    const res = await GET(req, createRouteParamsContext());
    const json = (await res.json()) as unknown[];

    expect(res.status).toBe(200);
    expect(mock.client.from).toHaveBeenCalledWith("itinerary_items");
    expect(mock.client.from).not.toHaveBeenCalledWith("trips");
    expect(json).toHaveLength(1);
  });

  it("returns 400 for invalid tripId query param", async () => {
    const mock = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mock.client as never));

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/itineraries?tripId=abc",
    });
    const res = await GET(req, createRouteParamsContext());
    expect(res.status).toBe(400);
  });

  it("filters by tripId when provided", async () => {
    const mock = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mock.client as never));

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/itineraries?tripId=123",
    });
    const res = await GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);

    const itineraryBuilder = mock.builders.find((b) => b.table === "itinerary_items");
    expect(itineraryBuilder).toBeTruthy();
    expect(itineraryBuilder?.eqCalls).toContainEqual(["trip_id", 123]);
    expect(itineraryBuilder?.eqCalls).toContainEqual(["user_id", baseItem.user_id]);
  });

  it("returns 400 for malformed JSON body", async () => {
    const mock = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mock.client as never));

    const req = createMockNextRequest({
      body: "{not-json",
      method: "POST",
      url: "http://localhost/api/itineraries",
    });
    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
  });

  it("returns 400 for invalid create payload", async () => {
    const mock = createSupabaseMock();
    setSupabaseFactoryForTests(() => Promise.resolve(mock.client as never));

    const req = createMockNextRequest({
      body: {},
      method: "POST",
      url: "http://localhost/api/itineraries",
    });
    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
  });

  it("returns 403 when trip is not found for user", async () => {
    const mock = createSupabaseMock({
      tripSingleResult: { data: null, error: { code: "PGRST116", message: "No rows" } },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mock.client as never));

    const req = createMockNextRequest({
      body: { itemType: "activity", title: "Museum", tripId: 123 },
      method: "POST",
      url: "http://localhost/api/itineraries",
    });
    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(403);
  });

  it("creates an itinerary item for the authenticated user", async () => {
    const mock = createSupabaseMock({
      insertResult: { data: baseItem, error: null },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mock.client as never));

    const req = createMockNextRequest({
      body: { itemType: "activity", title: "Museum", tripId: 123 },
      method: "POST",
      url: "http://localhost/api/itineraries",
    });
    const res = await POST(req, createRouteParamsContext());
    const json = (await res.json()) as ItineraryItemsRow;

    expect(res.status).toBe(201);
    expect(json.trip_id).toBe(123);
    expect(mock.client.from).toHaveBeenCalledWith("trips");
    expect(mock.client.from).toHaveBeenCalledWith("itinerary_items");

    const insertBuilder = mock.builders.find(
      (b) => b.table === "itinerary_items" && b.insertPayload !== null
    );
    expect(insertBuilder).toBeTruthy();
    expect(insertBuilder?.insertPayload).toMatchObject({ user_id: baseItem.user_id });
  });
});
