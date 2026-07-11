/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Tables } from "@/lib/supabase/database.types";
import { TEST_USER_ID } from "@/test/helpers/ids";
import { upsertItineraryItemImpl } from "./actions/itinerary";
import { createTripImpl } from "./actions/trips";

const mocks = vi.hoisted(() => ({
  deleteSingle: vi.fn(),
  getUser: vi.fn(),
  hashTelemetryIdentifier: vi.fn(),
  insertSingle: vi.fn(),
  recordTelemetryEvent: vi.fn(),
  updateSingle: vi.fn(),
  withTelemetrySpan: vi.fn(
    (_name: string, _options: unknown, execute: () => Promise<unknown>) => execute()
  ),
}));

vi.mock("server-only", () => ({}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(() => ({
    auth: { getUser: mocks.getUser },
  })),
}));

vi.mock("@/lib/supabase/typed-helpers", () => ({
  deleteSingle: mocks.deleteSingle,
  insertSingle: mocks.insertSingle,
  updateSingle: mocks.updateSingle,
}));

vi.mock("@/lib/telemetry/identifiers", () => ({
  hashTelemetryIdentifier: mocks.hashTelemetryIdentifier,
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  })),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: mocks.recordTelemetryEvent,
  withTelemetrySpan: mocks.withTelemetrySpan,
}));

const TRIP_ID = 42;
const ITEM_ID = 73;

const tripInput = {
  destination: "Tokyo, Japan",
  endDate: "2099-01-08",
  startDate: "2099-01-01",
  title: "Private trip title",
};

function tripRow(overrides: Partial<Tables<"trips">> = {}): Tables<"trips"> {
  return {
    budget: 0,
    created_at: "2099-01-01T00:00:00Z",
    currency: "USD",
    description: null,
    destination: "Tokyo, Japan",
    end_date: "2099-01-08",
    flexibility: null,
    id: TRIP_ID,
    name: "Private trip title",
    search_metadata: {},
    start_date: "2099-01-01",
    status: "planning",
    tags: null,
    travelers: 1,
    trip_type: "leisure",
    updated_at: "2099-01-01T00:00:00Z",
    user_id: TEST_USER_ID,
    ...overrides,
  };
}

function itineraryRow(
  overrides: Partial<Tables<"itinerary_items">> = {}
): Tables<"itinerary_items"> {
  return {
    booking_status: "completed",
    created_at: "2099-01-01T00:00:00Z",
    currency: "USD",
    description: null,
    end_time: null,
    external_id: null,
    id: ITEM_ID,
    item_type: "activity",
    location: null,
    metadata: {},
    price: null,
    start_time: null,
    title: "Private itinerary title",
    trip_id: TRIP_ID,
    updated_at: "2099-01-01T00:00:00Z",
    user_id: TEST_USER_ID,
    ...overrides,
  };
}

function itineraryInput(overrides: Record<string, unknown> = {}) {
  return {
    bookingStatus: "completed",
    itemType: "activity",
    payload: {},
    title: "Private itinerary title",
    tripId: TRIP_ID,
    ...overrides,
  };
}

function expectNoRawIdentifiersOrContent(): void {
  const emitted = JSON.stringify(mocks.recordTelemetryEvent.mock.calls);
  expect(emitted).not.toContain(TEST_USER_ID);
  expect(emitted).not.toContain(`trip:${TRIP_ID}`);
  expect(emitted).not.toContain(String(TRIP_ID));
  expect(emitted).not.toContain(String(ITEM_ID));
  expect(emitted).not.toContain("Tokyo, Japan");
  expect(emitted).not.toContain("Private trip title");
  expect(emitted).not.toContain("Private itinerary title");
}

describe("trip activation telemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getUser.mockResolvedValue({ data: { user: { id: TEST_USER_ID } } });
    mocks.hashTelemetryIdentifier.mockImplementation((identifier: string) => {
      if (identifier === TEST_USER_ID) return "stable-user-hash";
      if (identifier === `trip:${TRIP_ID}`) return "stable-trip-hash";
      return null;
    });
    mocks.recordTelemetryEvent.mockImplementation(() => undefined);
  });

  it("emits the canonical trip-created event after validated persistence", async () => {
    mocks.insertSingle.mockResolvedValue({ data: tripRow(), error: null });

    const result = await createTripImpl(tripInput);

    expect(result.ok).toBe(true);
    expect(mocks.recordTelemetryEvent).toHaveBeenCalledTimes(1);
    expect(mocks.recordTelemetryEvent).toHaveBeenCalledWith("activation.trip_created", {
      attributes: {
        "trip.id_hash": "stable-trip-hash",
        "user.id_hash": "stable-user-hash",
      },
    });
    expectNoRawIdentifiersOrContent();
  });

  it("omits identifier attributes when telemetry hashing is not configured", async () => {
    mocks.hashTelemetryIdentifier.mockReturnValue(null);
    mocks.insertSingle.mockResolvedValue({ data: tripRow(), error: null });

    const result = await createTripImpl(tripInput);

    expect(result.ok).toBe(true);
    expect(mocks.recordTelemetryEvent).toHaveBeenCalledWith("activation.trip_created", {
      attributes: {},
    });
  });

  it("does not emit for unauthorized or failed trip creation", async () => {
    mocks.getUser.mockResolvedValueOnce({ data: { user: null } });
    const unauthorized = await createTripImpl(tripInput);
    expect(unauthorized.ok).toBe(false);

    mocks.insertSingle.mockResolvedValueOnce({
      data: null,
      error: new Error("insert failed"),
    });
    const failed = await createTripImpl(tripInput);
    expect(failed.ok).toBe(false);

    expect(mocks.recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("does not emit when persisted rows fail application validation", async () => {
    mocks.insertSingle.mockResolvedValueOnce({
      data: { ...tripRow(), currency: "INVALID" },
      error: null,
    });
    const invalidTrip = await createTripImpl(tripInput);
    expect(invalidTrip.ok).toBe(false);

    mocks.insertSingle.mockResolvedValueOnce({
      data: itineraryRow({ booking_status: "unexpected" }),
      error: null,
    });
    const invalidItem = await upsertItineraryItemImpl(TRIP_ID, itineraryInput());
    expect(invalidItem.ok).toBe(false);

    expect(mocks.recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("preserves the successful action result when telemetry throws", async () => {
    mocks.insertSingle.mockResolvedValue({ data: tripRow(), error: null });
    mocks.recordTelemetryEvent.mockImplementation(() => {
      throw new Error("exporter unavailable");
    });

    const result = await createTripImpl(tripInput);

    expect(result.ok).toBe(true);
  });

  it("emits a completed-item create event with low-cardinality attributes", async () => {
    mocks.insertSingle.mockResolvedValue({ data: itineraryRow(), error: null });

    const result = await upsertItineraryItemImpl(TRIP_ID, itineraryInput());

    expect(result.ok).toBe(true);
    expect(mocks.recordTelemetryEvent).toHaveBeenCalledTimes(1);
    expect(mocks.recordTelemetryEvent).toHaveBeenCalledWith(
      "activation.itinerary_item_completed",
      {
        attributes: {
          "itinerary.item_type": "activity",
          "itinerary.operation": "create",
          "trip.id_hash": "stable-trip-hash",
          "user.id_hash": "stable-user-hash",
        },
      }
    );
    expect(mocks.withTelemetrySpan).toHaveBeenCalledWith(
      "trips.itinerary.upsert",
      { attributes: { "itinerary.operation": "upsert" } },
      expect.any(Function)
    );
    expectNoRawIdentifiersOrContent();
  });

  it("emits a completed-item update event from the validated returned row", async () => {
    mocks.updateSingle.mockResolvedValue({
      data: itineraryRow({ booking_status: "completed", item_type: "meal" }),
      error: null,
    });

    const result = await upsertItineraryItemImpl(
      TRIP_ID,
      itineraryInput({
        bookingStatus: "booked",
        id: ITEM_ID,
        itemType: "meal",
      })
    );

    expect(result.ok).toBe(true);
    expect(mocks.recordTelemetryEvent).toHaveBeenCalledWith(
      "activation.itinerary_item_completed",
      {
        attributes: {
          "itinerary.item_type": "meal",
          "itinerary.operation": "update",
          "trip.id_hash": "stable-trip-hash",
          "user.id_hash": "stable-user-hash",
        },
      }
    );
  });

  it("does not emit for non-completed, unauthorized, or failed itinerary mutations", async () => {
    mocks.insertSingle.mockResolvedValueOnce({
      data: itineraryRow({ booking_status: "booked" }),
      error: null,
    });
    const booked = await upsertItineraryItemImpl(TRIP_ID, itineraryInput());
    expect(booked.ok).toBe(true);

    mocks.getUser.mockResolvedValueOnce({ data: { user: null } });
    const unauthorized = await upsertItineraryItemImpl(TRIP_ID, itineraryInput());
    expect(unauthorized.ok).toBe(false);

    mocks.updateSingle.mockResolvedValueOnce({
      data: null,
      error: new Error("update failed"),
    });
    const failed = await upsertItineraryItemImpl(
      TRIP_ID,
      itineraryInput({ id: ITEM_ID })
    );
    expect(failed.ok).toBe(false);

    expect(mocks.recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("preserves a completed itinerary result when telemetry throws", async () => {
    mocks.insertSingle.mockResolvedValue({ data: itineraryRow(), error: null });
    mocks.recordTelemetryEvent.mockImplementation(() => {
      throw new Error("exporter unavailable");
    });

    const result = await upsertItineraryItemImpl(TRIP_ID, itineraryInput());

    expect(result.ok).toBe(true);
  });

  it("preserves a persisted result when identifier hashing throws", async () => {
    mocks.insertSingle.mockResolvedValue({ data: itineraryRow(), error: null });
    mocks.hashTelemetryIdentifier.mockImplementation(() => {
      throw new Error("hash configuration unavailable");
    });

    const result = await upsertItineraryItemImpl(TRIP_ID, itineraryInput());

    expect(result.ok).toBe(true);
    expect(mocks.recordTelemetryEvent).not.toHaveBeenCalled();
  });
});
