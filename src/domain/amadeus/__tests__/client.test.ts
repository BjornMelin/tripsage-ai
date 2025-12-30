/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Hoist mocks so they are available to vi.mock factory
const constructorMock = vi.hoisted(() => vi.fn());
const getMock = vi.hoisted(() => vi.fn());
const offersGetMock = vi.hoisted(() => vi.fn());
const bookingPostMock = vi.hoisted(() => vi.fn());

vi.mock("amadeus", () => {
  class AmadeusMock {
    constructor(config: unknown) {
      constructorMock(config);
    }

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

describe("Amadeus client wrapper", () => {
  beforeEach(() => {
    process.env.AMADEUS_CLIENT_ID = "test-amadeus-client-id";
    process.env.AMADEUS_CLIENT_SECRET = "test-amadeus-client-secret";
    process.env.AMADEUS_ENV = "test";
    constructorMock.mockReset();
    getMock.mockReset();
    offersGetMock.mockReset();
    bookingPostMock.mockReset();
    vi.resetModules();
  });

  it("creates singleton client using env vars", async () => {
    const { getAmadeusClient } = await import("../client");
    const c1 = getAmadeusClient();
    const c2 = getAmadeusClient();
    expect(c1).toBe(c2);
    expect(constructorMock).toHaveBeenCalledTimes(1);
    expect(constructorMock).toHaveBeenCalledWith(
      expect.objectContaining({
        clientId: "test-amadeus-client-id",
        clientSecret: "test-amadeus-client-secret",
        hostname: "test",
      })
    );
  });

  it("delegates geocode and offers calls", async () => {
    const { listHotelsByGeocode, searchHotelOffers } = await import("../client");
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
    const { bookHotelOffer } = await import("../client");
    await bookHotelOffer({ data: {} });
    expect(bookingPostMock).toHaveBeenCalled();
  });
});
