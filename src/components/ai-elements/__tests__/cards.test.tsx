/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DestinationCard } from "@/components/ai-elements/destination-card";
import { FlightOfferCard } from "@/components/ai-elements/flight-card";
import { ItineraryTimeline } from "@/components/ai-elements/itinerary-timeline";
import { StayCard } from "@/components/ai-elements/stay-card";

describe("AI Elements Cards", () => {
  it("renders FlightOfferCard with itineraries and sources", () => {
    render(
      <FlightOfferCard
        result={{
          currency: "USD",
          fromCache: false,
          itineraries: [
            {
              id: "it-1",
              price: 320.5,
              segments: [
                {
                  arrival: "2025-12-15T16:00:00Z",
                  carrier: "AA",
                  departure: "2025-12-15T08:00:00Z",
                  destination: "JFK",
                  origin: "SFO",
                },
              ],
            },
          ],
          offers: [],
          provider: "duffel",
          schemaVersion: "flight.v2",
          sources: [{ title: "Example", url: "https://example.com" }],
        }}
      />
    );
    expect(screen.getByText(/Flight Options/)).toBeInTheDocument();
    expect(screen.getByText(/SFO → JFK/)).toBeInTheDocument();
  });

  it("renders StayCard with stays and sources", () => {
    render(
      <StayCard
        result={{
          schemaVersion: "stay.v1",
          sources: [{ title: "Source", url: "https://example.com/s" }],
          stays: [
            { address: "123 Ave", currency: "USD", name: "Hotel A", nightlyRate: 180 },
          ],
        }}
      />
    );
    expect(screen.getByText(/Places to Stay/)).toBeInTheDocument();
    expect(screen.getByText(/Hotel A/)).toBeInTheDocument();
  });

  it("does not render unsafe flight booking links", () => {
    render(
      <FlightOfferCard
        result={{
          currency: "USD",
          fromCache: false,
          itineraries: [
            {
              bookingUrl: "javascript:alert(1)",
              id: "it-unsafe",
              price: 320.5,
              segments: [
                {
                  arrival: "2025-12-15T16:00:00Z",
                  departure: "2025-12-15T08:00:00Z",
                  destination: "JFK",
                  origin: "SFO",
                },
              ],
            },
          ],
          offers: [],
          provider: "duffel",
          schemaVersion: "flight.v2",
          sources: [],
        }}
      />
    );

    expect(screen.queryByRole("link", { name: "Book" })).toBeNull();
  });

  it("does not render unsafe stay links", () => {
    render(
      <StayCard
        result={{
          schemaVersion: "stay.v1",
          sources: [],
          stays: [
            {
              address: "123 Ave",
              currency: "USD",
              name: "Hotel A",
              nightlyRate: 180,
              url: "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            },
          ],
        }}
      />
    );

    expect(screen.queryByRole("link", { name: "View" })).toBeNull();
  });

  it("does not render unsafe destination attraction links", () => {
    render(
      <DestinationCard
        result={{
          attractions: [
            {
              title: "Museum",
              url: "javascript:alert(1)",
            },
          ],
          destination: "Paris",
          schemaVersion: "dest.v1",
          sources: [],
        }}
      />
    );

    expect(screen.queryByRole("link", { name: "Learn more" })).toBeNull();
  });

  it("does not render unsafe itinerary activity links", () => {
    render(
      <ItineraryTimeline
        result={{
          days: [
            {
              activities: [
                {
                  name: "Walk",
                  url: "//evil.example/path",
                },
              ],
              day: 1,
            },
          ],
          destination: "Paris",
          schemaVersion: "itin.v1",
          sources: [],
        }}
      />
    );

    expect(screen.queryByRole("link", { name: "Learn more" })).toBeNull();
  });
});
