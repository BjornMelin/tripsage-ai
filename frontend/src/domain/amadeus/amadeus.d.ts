/**
 * @fileoverview TypeScript declarations for the amadeus npm package.
 *
 * The amadeus package does not include TypeScript definitions, so we provide
 * minimal type declarations based on the actual API usage patterns.
 *
 * Note: API response validation is handled separately via Zod schemas in
 * `schemas.ts`. This declaration file only provides types for the SDK client
 * methods themselves.
 */

declare module "amadeus" {
  /** Configuration for the Amadeus client. */
  interface AmadeusConfig {
    clientId: string;
    clientSecret: string;
    hostname?: string;
  }

  /** Response from the Amadeus API. */
  interface AmadeusResponse<T = unknown> {
    data?: T;
    result?: T;
    [key: string]: unknown;
  }

  /** Amadeus client interface. */
  interface AmadeusClient {
    referenceData: {
      locations: {
        hotels: {
          byGeocode: {
            get(params: {
              latitude: number;
              longitude: number;
              radius?: number;
              radiusUnit?: string;
            }): Promise<AmadeusResponse>;
          };
        };
      };
    };
    shopping: {
      hotelOffersSearch: {
        get(params: {
          adults: number;
          checkInDate: string;
          checkOutDate: string;
          currency?: string;
          hotelIds: string;
          includeClosed?: boolean;
        }): Promise<AmadeusResponse>;
      };
    };
    booking: {
      hotelBookings: {
        post(payload: string): Promise<AmadeusResponse>;
      };
    };
  }

  /** Amadeus client class. */
  class Amadeus implements AmadeusClient {
    constructor(config: AmadeusConfig);
    referenceData: AmadeusClient["referenceData"];
    shopping: AmadeusClient["shopping"];
    booking: AmadeusClient["booking"];
  }

  /** Export the Amadeus client class. */
  export default Amadeus;
}
