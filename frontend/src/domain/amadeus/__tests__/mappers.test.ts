import { describe, expect, it } from "vitest";
import { mapHotelsToListings } from "../mappers";
import type { AmadeusHotelOffer } from "../schemas";

describe("mapHotelsToListings", () => {
  it("maps hotels and offers into accommodation listings", () => {
    const hotels = [
      {
        address: { cityName: "Paris" },
        geoCode: { latitude: 48.8566, longitude: 2.3522 },
        hotelId: "H1",
        name: "Hotel One",
      },
    ];

    const offersByHotel: Record<string, AmadeusHotelOffer[]> = {
      H1: [
        {
          checkInDate: "2025-12-01",
          checkOutDate: "2025-12-05",
          id: "OFFER1",
          price: { currency: "EUR", total: "500.00" },
        },
      ],
    };

    const listings = mapHotelsToListings(hotels as any, offersByHotel, {
      checkin: "2025-12-01",
      checkout: "2025-12-05",
      guests: 2,
    });

    expect(listings).toHaveLength(1);
    const listing = listings[0] as any;
    expect(listing.id).toBe("H1");
    expect(listing.provider).toBe("amadeus");
    expect(listing.rooms[0].rates[0].price.total).toBe("500.00");
  });
});
