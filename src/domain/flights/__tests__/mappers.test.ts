/** @vitest-environment node */

import { describe, expect, it } from "vitest";

import { mapDuffelOffer, mapDuffelOffersList } from "../mappers";

// Sample Duffel segment with all fields populated
const createDuffelSegment = (overrides = {}) => ({
  arriving_at: "2025-06-15T14:30:00Z",
  departing_at: "2025-06-15T10:00:00Z",
  destination: {
    city_name: "Paris",
    country_name: "France",
    iata_code: "CDG",
    name: "Charles de Gaulle Airport",
    terminal: "2E",
  },
  duration: "PT4H30M",
  marketing_carrier: { iata_code: "AF", name: "Air France" },
  marketing_carrier_flight_number: "AF123",
  operating_carrier: { iata_code: "AF", name: "Air France" },
  operating_carrier_flight_number: "AF123",
  origin: {
    city_name: "New York",
    country_name: "United States",
    iata_code: "JFK",
    name: "John F. Kennedy International Airport",
    terminal: "1",
  },
  ...overrides,
});

// Sample Duffel slice
const createDuffelSlice = (overrides = {}) => ({
  cabin_class: "economy",
  duration: "PT4H30M",
  segments: [createDuffelSegment()],
  ...overrides,
});

// Sample Duffel offer
const createDuffelOffer = (overrides = {}) => ({
  id: "off_test_123",
  slices: [createDuffelSlice()],
  total_amount: "450.00",
  total_currency: "USD",
  ...overrides,
});

describe("mapDuffelOffer", () => {
  it("should map a valid Duffel offer to FlightOffer", () => {
    const offer = createDuffelOffer();
    const result = mapDuffelOffer(offer);

    expect(result).not.toBeNull();
    expect(result?.id).toBe("off_test_123");
    expect(result?.provider).toBe("duffel");
    expect(result?.price).toEqual({ amount: 450, currency: "USD" });
    expect(result?.slices).toHaveLength(1);
    expect(result?.slices[0].cabinClass).toBe("economy");
    expect(result?.slices[0].segments).toHaveLength(1);
  });

  it("should map segment details correctly", () => {
    const offer = createDuffelOffer();
    const result = mapDuffelOffer(offer);
    expect(result).not.toBeNull();

    const segment = result?.slices[0].segments[0];
    expect(segment).toBeDefined();
    expect(segment?.origin.iata).toBe("JFK");
    expect(segment?.origin.city).toBe("New York");
    expect(segment?.origin.airport).toBe("John F. Kennedy International Airport");
    expect(segment?.origin.terminal).toBe("1");
    expect(segment?.destination.iata).toBe("CDG");
    expect(segment?.destination.city).toBe("Paris");
    expect(segment?.flightNumber).toBe("AF123");
    expect(segment?.carrier).toBe("Air France");
    expect(segment?.departureTime).toBe("2025-06-15T10:00:00Z");
    expect(segment?.arrivalTime).toBe("2025-06-15T14:30:00Z");
  });

  it("should parse ISO duration to minutes", () => {
    const offer = createDuffelOffer();
    const result = mapDuffelOffer(offer);

    expect(result?.slices[0].segments[0].durationMinutes).toBe(270); // 4h30m = 270 minutes
  });

  it("should handle duration with days", () => {
    const offer = createDuffelOffer({
      slices: [
        createDuffelSlice({
          segments: [createDuffelSegment({ duration: "P1DT2H30M" })],
        }),
      ],
    });
    const result = mapDuffelOffer(offer);

    // 1 day (1440) + 2 hours (120) + 30 minutes = 1590
    expect(result?.slices[0].segments[0].durationMinutes).toBe(1590);
  });

  it("should return null for offer without id", () => {
    const offer = createDuffelOffer({ id: undefined });
    const result = mapDuffelOffer(offer);

    expect(result).toBeNull();
  });

  it("should return null for offer with empty slices", () => {
    const offer = createDuffelOffer({ slices: [] });
    const result = mapDuffelOffer(offer);

    expect(result).toBeNull();
  });

  it("should filter out segments with missing origin IATA code", () => {
    const offer = createDuffelOffer({
      slices: [
        createDuffelSlice({
          segments: [
            createDuffelSegment({ origin: { iata_code: "", name: "Unknown" } }),
          ],
        }),
      ],
    });
    const result = mapDuffelOffer(offer);

    // Segment is filtered out, slice becomes empty, offer is null
    expect(result).toBeNull();
  });

  it("should filter out segments with missing destination IATA code", () => {
    const offer = createDuffelOffer({
      slices: [
        createDuffelSlice({
          segments: [
            createDuffelSegment({ destination: { iata_code: "", name: "Unknown" } }),
          ],
        }),
      ],
    });
    const result = mapDuffelOffer(offer);

    expect(result).toBeNull();
  });

  it("should default currency to USD when missing", () => {
    const offer = createDuffelOffer({ total_currency: undefined });
    const result = mapDuffelOffer(offer);

    expect(result?.price.currency).toBe("USD");
  });

  it("should throw when amount is missing (schema requires amount > 0)", () => {
    const offer = createDuffelOffer({ total_amount: undefined });
    // The FLIGHT_OFFER_SCHEMA requires price.amount > 0, so this throws
    expect(() => mapDuffelOffer(offer)).toThrow();
  });

  it("should default cabin class to economy when missing", () => {
    const offer = createDuffelOffer({
      slices: [createDuffelSlice({ cabin_class: undefined })],
    });
    const result = mapDuffelOffer(offer);

    expect(result?.slices[0].cabinClass).toBe("economy");
  });

  it("should use marketing carrier when operating carrier name is missing", () => {
    const offer = createDuffelOffer({
      slices: [
        createDuffelSlice({
          segments: [
            createDuffelSegment({
              marketing_carrier: { iata_code: "DL", name: "Delta Air Lines" },
              operating_carrier: { iata_code: "DL", name: undefined },
            }),
          ],
        }),
      ],
    });
    const result = mapDuffelOffer(offer);

    expect(result?.slices[0].segments[0].carrier).toBe("Delta Air Lines");
  });

  it("should handle multiple slices (round trip)", () => {
    const offer = createDuffelOffer({
      slices: [
        createDuffelSlice(), // outbound
        createDuffelSlice({
          segments: [
            createDuffelSegment({
              destination: { city_name: "New York", iata_code: "JFK", name: "JFK" },
              origin: { city_name: "Paris", iata_code: "CDG", name: "CDG" },
            }),
          ],
        }), // return
      ],
    });
    const result = mapDuffelOffer(offer);

    expect(result?.slices).toHaveLength(2);
    expect(result?.slices[0].segments[0].origin.iata).toBe("JFK");
    expect(result?.slices[1].segments[0].origin.iata).toBe("CDG");
  });

  it("should handle connecting flights (multiple segments)", () => {
    const offer = createDuffelOffer({
      slices: [
        createDuffelSlice({
          segments: [
            createDuffelSegment(), // JFK -> CDG
            createDuffelSegment({
              destination: { city_name: "Rome", iata_code: "FCO", name: "Fiumicino" },
              origin: { city_name: "Paris", iata_code: "CDG", name: "CDG" },
            }), // CDG -> FCO
          ],
        }),
      ],
    });
    const result = mapDuffelOffer(offer);

    expect(result?.slices[0].segments).toHaveLength(2);
    expect(result?.slices[0].segments[0].destination.iata).toBe("CDG");
    expect(result?.slices[0].segments[1].destination.iata).toBe("FCO");
  });
});

describe("mapDuffelOffersList", () => {
  it("should map Duffel response with data.offers array", () => {
    const payload = {
      data: {
        offers: [createDuffelOffer()],
      },
    };
    const result = mapDuffelOffersList(payload, "EUR");

    expect(result.offers).toHaveLength(1);
    expect(result.currency).toBe("USD"); // resolved from offer
    expect(result.itineraries).toHaveLength(1);
  });

  it("should map Duffel response with data as array", () => {
    const payload = {
      data: [createDuffelOffer()],
    };
    const result = mapDuffelOffersList(payload, "EUR");

    expect(result.offers).toHaveLength(1);
  });

  it("should use fallback currency when no offers have currency", () => {
    const payload = {
      data: {
        offers: [],
      },
    };
    const result = mapDuffelOffersList(payload, "EUR");

    expect(result.currency).toBe("EUR");
  });

  it("should filter out invalid offers", () => {
    const payload = {
      data: {
        offers: [
          createDuffelOffer(), // valid
          createDuffelOffer({ id: undefined }), // invalid - no id
          createDuffelOffer({ slices: [] }), // invalid - no slices
        ],
      },
    };
    const result = mapDuffelOffersList(payload, "USD");

    expect(result.offers).toHaveLength(1);
    expect(result.itineraries).toHaveLength(1);
  });

  it("should build itineraries with flattened segments", () => {
    const payload = {
      data: {
        offers: [
          createDuffelOffer({
            slices: [
              createDuffelSlice({
                segments: [
                  createDuffelSegment(),
                  createDuffelSegment({
                    destination: { city_name: "Rome", iata_code: "FCO", name: "FCO" },
                    origin: { city_name: "Paris", iata_code: "CDG", name: "CDG" },
                  }),
                ],
              }),
            ],
          }),
        ],
      },
    };
    const result = mapDuffelOffersList(payload, "USD");

    expect(result.itineraries[0].segments).toHaveLength(2);
    expect(result.itineraries[0].segments[0].origin).toBe("JFK");
    expect(result.itineraries[0].segments[0].destination).toBe("CDG");
    expect(result.itineraries[0].segments[1].origin).toBe("CDG");
    expect(result.itineraries[0].segments[1].destination).toBe("FCO");
  });

  it("should extract itinerary fields correctly", () => {
    const payload = {
      data: {
        offers: [createDuffelOffer()],
      },
    };
    const result = mapDuffelOffersList(payload, "USD");

    const itinerary = result.itineraries[0];
    expect(itinerary.id).toBe("off_test_123");
    expect(itinerary.price).toBe(450);
    expect(itinerary.bookingUrl).toBeUndefined();
    expect(itinerary.segments[0].flightNumber).toBe("AF123");
    expect(itinerary.segments[0].carrier).toBe("Air France");
    expect(itinerary.segments[0].departure).toBe("2025-06-15T10:00:00Z");
    expect(itinerary.segments[0].arrival).toBe("2025-06-15T14:30:00Z");
  });

  it("should handle empty payload gracefully", () => {
    const result = mapDuffelOffersList({}, "USD");

    expect(result.offers).toEqual([]);
    expect(result.itineraries).toEqual([]);
    expect(result.currency).toBe("USD");
  });

  it("should handle null payload gracefully", () => {
    const result = mapDuffelOffersList(null, "USD");

    expect(result.offers).toEqual([]);
    expect(result.itineraries).toEqual([]);
    expect(result.currency).toBe("USD");
  });

  it("should handle undefined payload gracefully", () => {
    const result = mapDuffelOffersList(undefined, "GBP");

    expect(result.offers).toEqual([]);
    expect(result.itineraries).toEqual([]);
    expect(result.currency).toBe("GBP");
  });

  it("should silently skip offers that throw during mapping", () => {
    // Create a malformed offer that would cause schema.parse to throw
    const payload = {
      data: {
        offers: [
          createDuffelOffer(),
          {
            // This has id but segments that would fail validation
            id: "off_malformed",
            slices: [
              {
                cabin_class: "invalid_class_that_might_fail",
                segments: [
                  {
                    destination: { iata_code: "BBB" },
                    origin: { iata_code: "AAA" },
                  },
                ],
              },
            ],
            total_amount: "not_a_number",
          },
        ],
      },
    };
    const result = mapDuffelOffersList(payload, "USD");

    // Should have at least the valid offer
    expect(result.offers.length).toBeGreaterThanOrEqual(1);
  });
});
