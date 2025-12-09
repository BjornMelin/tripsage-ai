/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { mapHotelsToListings } from "../mappers";
import type { AmadeusHotelOffer } from "../schemas";

describe("mapHotelsToListings", () => {
  const baseOffers: Record<string, AmadeusHotelOffer[]> = {
    H1: [
      {
        checkInDate: "2025-12-01",
        checkOutDate: "2025-12-05",
        id: "OFFER1",
        price: { currency: "EUR", total: "500.00" },
      },
    ],
  };

  const baseMeta = {
    checkin: "2025-12-01",
    checkout: "2025-12-05",
    guests: 2,
  };

  it("maps hotels and offers into accommodation listings", () => {
    const hotels = [
      {
        address: { cityName: "Paris" },
        geoCode: { latitude: 48.8566, longitude: 2.3522 },
        hotelId: "H1",
        name: "Hotel One",
      },
    ];

    const listings = mapHotelsToListings(hotels, baseOffers, baseMeta);

    expect(listings).toHaveLength(1);
    const listing = listings[0] as Record<string, unknown>;
    expect(listing.id).toBe("H1");
    expect(listing.name).toBe("Hotel One");
    const rooms = listing.rooms as Array<Record<string, unknown>>;
    const rates = rooms[0].rates as Array<{ price: { total: string } }>;
    expect(rates[0].price.total).toBe("500.00");
  });

  it("passes through geoCode for distance calculations", () => {
    const hotels = [
      {
        address: { cityName: "Paris" },
        geoCode: { latitude: 48.8566, longitude: 2.3522 },
        hotelId: "H1",
        name: "Hotel One",
      },
    ];

    const listings = mapHotelsToListings(hotels, baseOffers, baseMeta);
    const listing = listings[0] as Record<string, unknown>;

    expect(listing.geoCode).toEqual({ latitude: 48.8566, longitude: 2.3522 });
  });

  it("handles hotels without geoCode", () => {
    const hotels = [
      {
        address: { cityName: "Paris" },
        hotelId: "H1",
        name: "Hotel One",
        // No geoCode
      },
    ];

    const listings = mapHotelsToListings(hotels, baseOffers, baseMeta);
    const listing = listings[0] as Record<string, unknown>;

    expect(listing.geoCode).toBeUndefined();
  });

  it("maps multiple hotels preserving individual geoCode values", () => {
    const hotels = [
      {
        address: { cityName: "Paris" },
        geoCode: { latitude: 48.8566, longitude: 2.3522 },
        hotelId: "H1",
        name: "Hotel Paris",
      },
      {
        address: { cityName: "London" },
        geoCode: { latitude: 51.5074, longitude: -0.1278 },
        hotelId: "H2",
        name: "Hotel London",
      },
    ];

    const offersMulti: Record<string, AmadeusHotelOffer[]> = {
      H1: baseOffers.H1,
      H2: [
        {
          checkInDate: "2025-12-01",
          checkOutDate: "2025-12-05",
          id: "OFFER2",
          price: { currency: "GBP", total: "300.00" },
        },
      ],
    };

    const listings = mapHotelsToListings(hotels, offersMulti, baseMeta);

    expect(listings).toHaveLength(2);
    const parisListing = listings[0] as Record<string, unknown>;
    const londonListing = listings[1] as Record<string, unknown>;

    expect(parisListing.geoCode).toEqual({ latitude: 48.8566, longitude: 2.3522 });
    expect(londonListing.geoCode).toEqual({ latitude: 51.5074, longitude: -0.1278 });
  });
});
