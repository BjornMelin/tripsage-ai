/** @vitest-environment node */

import { savePlaceToTrip } from "@ai/tools";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

function isAsyncIterable(value: unknown): value is AsyncIterable<unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { [Symbol.asyncIterator]?: unknown })[Symbol.asyncIterator] ===
      "function"
  );
}

async function resolveToolResult<T>(
  value: T | AsyncIterable<T> | undefined
): Promise<T> {
  if (value === undefined) {
    throw new Error("Tool returned undefined output");
  }

  if (isAsyncIterable(value)) {
    let last: T | undefined;
    for await (const chunk of value) {
      last = chunk as T;
    }
    if (last === undefined) {
      throw new Error("AsyncIterable produced no values");
    }
    return last;
  }

  return value;
}

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _options, fn) =>
    fn({
      addEvent: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
}));

const supabaseState = {
  sessionUserId: "user-123",
  upsertError: null as null | { code?: string; message: string },
};

const upsertMock = vi.fn(async () => ({ error: supabaseState.upsertError }));
const fromMock = vi.fn(() => ({ upsert: upsertMock }));
const getUserMock = vi.fn(async () => ({
  data: { user: { id: supabaseState.sessionUserId } },
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: async () => ({
    auth: { getUser: getUserMock },
    from: fromMock,
  }),
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  }),
}));

describe("tripsSavePlace tool", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    supabaseState.sessionUserId = "user-123";
    supabaseState.upsertError = null;
  });

  it("upserts saved_places with normalized place id", async () => {
    const raw = await savePlaceToTrip.execute?.(
      {
        place: { name: "Cafe", placeId: "places/mock-1", types: [] },
        tripId: 42,
        userId: "user-123",
      },
      mockContext
    );
    const result = await resolveToolResult(raw);

    expect(fromMock).toHaveBeenCalledWith("saved_places");
    expect(upsertMock).toHaveBeenCalledWith(
      expect.objectContaining({
        place_id: "mock-1",
        place_snapshot: expect.objectContaining({
          place: expect.objectContaining({ placeId: "mock-1" }),
        }),
        trip_id: 42,
        user_id: "user-123",
      }),
      expect.objectContaining({ onConflict: "trip_id,place_id" })
    );
    expect(result).toMatchObject({
      place: { name: "Cafe", placeId: "mock-1" },
    });
    expect(typeof result.savedAt).toBe("string");
  });

  it("throws when session user does not match injected userId", async () => {
    supabaseState.sessionUserId = "user-999";
    await expect(
      savePlaceToTrip.execute?.(
        {
          place: { name: "Cafe", placeId: "mock-1", types: [] },
          tripId: 42,
          userId: "user-123",
        },
        mockContext
      )
    ).rejects.toThrow(/unauthorized/i);
  });
});
