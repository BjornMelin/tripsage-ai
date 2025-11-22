import { beforeEach, describe, expect, it, vi } from "vitest";

// Hoist mocks so they are available to vi.mock factory
const getMock = vi.hoisted(() => vi.fn());
const offersGetMock = vi.hoisted(() => vi.fn());
const bookingPostMock = vi.hoisted(() => vi.fn());

vi.mock("amadeus", () => {
  class AmadeusMock {
    booking = { hotelBookings: { post: bookingPostMock } };
    referenceData = { locations: { hotels: { byGeocode: { get: getMock } } } };
    shopping = { hotelOffersSearch: { get: offersGetMock } };
  }
  return {
    // biome-ignore lint/style/useNamingConvention: required by mock interop
    __esModule: true,
    default: AmadeusMock,
  };
});

import {
  bookHotelOffer,
  getAmadeusClient,
  listHotelsByGeocode,
  searchHotelOffers,
  setAmadeusClientForTests,
} from "../client";

describe("Amadeus client wrapper", () => {
  beforeEach(() => {
    process.env.AMADEUS_CLIENT_ID = "id";
    process.env.AMADEUS_CLIENT_SECRET = "secret";
    process.env.AMADEUS_ENV = "test";
    getMock.mockReset();
    offersGetMock.mockReset();
    bookingPostMock.mockReset();
    setAmadeusClientForTests({
      booking: { hotelBookings: { post: bookingPostMock } },
      referenceData: { locations: { hotels: { byGeocode: { get: getMock } } } },
      shopping: { hotelOffersSearch: { get: offersGetMock } },
    } as never);
  });

  it("creates singleton client using env vars", () => {
    const c1 = getAmadeusClient();
    const c2 = getAmadeusClient();
    expect(c1).toBe(c2);
  });

  it("delegates geocode and offers calls", async () => {
    await listHotelsByGeocode({ latitude: 1, longitude: 2 });
    expect(getMock).toHaveBeenCalled();

    await searchHotelOffers({
      adults: 1,
      checkInDate: "2025-12-01",
      checkOutDate: "2025-12-02",
      hotelIds: ["H1"],
    });
    expect(offersGetMock).toHaveBeenCalled();
  });

  it("posts booking payload", async () => {
    await bookHotelOffer({ data: {} });
    expect(bookingPostMock).toHaveBeenCalled();
  });
});
