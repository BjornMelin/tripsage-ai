/** @vitest-environment jsdom */

import { describe, expect, it } from "vitest";

describe("useTripItineraryStore", () => {
  it("adds, updates, and removes destinations per trip", async () => {
    const { useTripItineraryStore } = await import("../trip-itinerary-store");
    localStorage.removeItem("trip-storage");
    useTripItineraryStore.setState({ destinationsByTripId: {} });

    const tripId = "trip-123";
    const destination = { country: "France", id: "dest-1", name: "Paris" };

    useTripItineraryStore.getState().addDestination(tripId, destination);
    expect(useTripItineraryStore.getState().destinationsByTripId[tripId]).toEqual([
      destination,
    ]);

    useTripItineraryStore
      .getState()
      .updateDestination(tripId, "dest-1", { name: "Paris (Updated)" });
    expect(useTripItineraryStore.getState().destinationsByTripId[tripId]?.[0]).toEqual({
      country: "France",
      id: "dest-1",
      name: "Paris (Updated)",
    });

    useTripItineraryStore.getState().removeDestination(tripId, "dest-1");
    expect(
      useTripItineraryStore.getState().destinationsByTripId[tripId]
    ).toBeUndefined();
  });

  it("sets destination order explicitly", async () => {
    const { useTripItineraryStore } = await import("../trip-itinerary-store");
    localStorage.removeItem("trip-storage");
    useTripItineraryStore.setState({ destinationsByTripId: {} });

    const tripId = "trip-1";
    const destinations = [
      { country: "US", id: "a", name: "Austin" },
      { country: "US", id: "b", name: "Boston" },
    ];

    useTripItineraryStore.getState().setDestinations(tripId, destinations);
    expect(useTripItineraryStore.getState().destinationsByTripId[tripId]).toEqual(
      destinations
    );
  });
});
