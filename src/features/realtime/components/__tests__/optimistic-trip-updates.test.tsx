/** @vitest-environment jsdom */

import type { UiTrip } from "@schemas/trips";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, renderWithProviders, screen } from "@/test/test-utils";
import { withFakeTimers } from "@/test/utils/with-fake-timers";

const MOCK_RECORD_CLIENT_ERROR_ON_ACTIVE_SPAN = vi.hoisted(() => vi.fn());
const MOCK_MUTATE_ASYNC = vi.hoisted(() => vi.fn());
const MOCK_USE_TRIP = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: MOCK_RECORD_CLIENT_ERROR_ON_ACTIVE_SPAN,
}));

vi.mock("@/hooks/use-current-user-id", () => ({
  useCurrentUserId: () => "user-123",
}));

vi.mock("@/hooks/use-trips", () => ({
  useTrip: MOCK_USE_TRIP,
  useUpdateTrip: () => ({
    mutateAsync: MOCK_MUTATE_ASYNC,
  }),
}));

import {
  ApplyTripUpdateToUiTrip,
  OptimisticTripUpdates,
} from "../optimistic-trip-updates";

const BASE_TRIP: UiTrip = {
  budget: 1200,
  createdAt: "2026-01-01T00:00:00.000Z",
  currency: "USD",
  destination: "Paris",
  destinations: [],
  endDate: "2026-05-09",
  id: "42",
  startDate: "2026-05-01",
  title: "Original Trip",
  travelers: 2,
  updatedAt: "2026-01-02T00:00:00.000Z",
  visibility: "private",
};

describe("applyTripUpdateToUiTrip", () => {
  beforeEach(() => {
    MOCK_RECORD_CLIENT_ERROR_ON_ACTIVE_SPAN.mockReset();
    MOCK_MUTATE_ASYNC.mockReset();
    MOCK_MUTATE_ASYNC.mockResolvedValue(BASE_TRIP);
    MOCK_USE_TRIP.mockReset();
    MOCK_USE_TRIP.mockReturnValue({
      data: BASE_TRIP,
      error: null,
      isConnected: true,
      isLoading: false,
      realtimeStatus: { errors: [] },
    });
  });

  it("maps database update fields to the UI trip shape", () => {
    const updated = ApplyTripUpdateToUiTrip({
      field: "name",
      prev: BASE_TRIP,
      tripId: 42,
      value: "Updated Trip",
    });

    expect(updated.title).toBe("Updated Trip");
    expect(updated.budget).toBe(BASE_TRIP.budget);
    expect(updated.destination).toBe(BASE_TRIP.destination);
    expect(updated.updatedAt).not.toBe(BASE_TRIP.updatedAt);
    expect(MOCK_RECORD_CLIENT_ERROR_ON_ACTIVE_SPAN).not.toHaveBeenCalled();
  });

  it("ignores non-finite numeric optimistic updates", () => {
    const updated = ApplyTripUpdateToUiTrip({
      field: "budget",
      prev: BASE_TRIP,
      tripId: 42,
      value: Number.NaN,
    });

    expect(updated).toBe(BASE_TRIP);
    expect(MOCK_RECORD_CLIENT_ERROR_ON_ACTIVE_SPAN).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        action: "applyOptimisticTripUpdate",
        field: "budget",
      })
    );
  });

  it("ignores unmapped fields and records sanitized telemetry", () => {
    const updated = ApplyTripUpdateToUiTrip({
      field: "description",
      prev: BASE_TRIP,
      tripId: 42,
      value: "private details",
    });

    expect(updated).toBe(BASE_TRIP);
    expect(MOCK_RECORD_CLIENT_ERROR_ON_ACTIVE_SPAN).toHaveBeenCalledWith(
      expect.any(Error),
      {
        action: "applyOptimisticTripUpdate",
        context: "OptimisticTripUpdates",
        field: "description",
        tripId: 42,
        valueType: "string",
      }
    );
  });

  it("keeps the ignored-field fallback stable when telemetry fails", () => {
    MOCK_RECORD_CLIENT_ERROR_ON_ACTIVE_SPAN.mockImplementationOnce(() => {
      throw new Error("telemetry unavailable");
    });

    const updated = ApplyTripUpdateToUiTrip({
      field: "search_metadata",
      prev: BASE_TRIP,
      tripId: 42,
      value: { source: "test" },
    });

    expect(updated).toBe(BASE_TRIP);
  });

  it(
    "timestamps optimistic update feed entries from the canonical clock helper",
    withFakeTimers(() => {
      const fixedNowIso = "2026-02-03T04:05:06.000Z";
      const expectedTime = new Date(fixedNowIso).toLocaleTimeString();
      vi.setSystemTime(new Date(fixedNowIso));
      MOCK_MUTATE_ASYNC.mockImplementationOnce(
        () => new Promise<never>(() => undefined)
      );

      renderWithProviders(<OptimisticTripUpdates tripId={42} />);

      fireEvent.change(screen.getByLabelText("Trip Name"), {
        target: { value: "Updated Trip" },
      });
      fireEvent.blur(screen.getByLabelText("Trip Name"));

      expect(screen.getByText("Updated name")).toBeInTheDocument();
      expect(screen.getByText(expectedTime)).toBeInTheDocument();
      expect(MOCK_MUTATE_ASYNC).toHaveBeenCalledWith({
        data: { name: "Updated Trip" },
        tripId: 42,
      });
    })
  );
});
