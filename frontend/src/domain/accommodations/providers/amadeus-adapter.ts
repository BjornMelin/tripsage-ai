/**
 * @fileoverview Amadeus Self-Service provider adapter with retry/backoff and telemetry.
 */

import { ProviderError } from "@domain/accommodations/errors";
import {
  bookHotelOffer,
  listHotelsByGeocode,
  searchHotelOffers,
} from "@domain/amadeus/client";
import { mapHotelsToListings } from "@domain/amadeus/mappers";
import {
  amadeusHotelBookingSchema,
  amadeusHotelOfferContainerSchema,
  amadeusHotelSchema,
} from "@domain/amadeus/schemas";
import type {
  AccommodationBookingRequest,
  AccommodationCheckAvailabilityParams,
  AccommodationDetailsParams,
  AccommodationSearchParams,
} from "@schemas/accommodations";
import { retryWithBackoff } from "@/lib/http/retry";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import type {
  AccommodationProviderAdapter,
  ProviderAvailabilityResult,
  ProviderBookingPayload,
  ProviderBookingResult,
  ProviderContext,
  ProviderDetailsResult,
  ProviderResult,
  ProviderSearchResult,
} from "./types";

const DEFAULT_RETRYABLE_CODES = new Set([429, 408, 500, 502, 503, 504]);

export function mapStatusToProviderCode(statusCode?: number): ProviderError["code"] {
  if (statusCode === 401 || statusCode === 403) return "unauthorized";
  if (statusCode === 404) return "not_found";
  if (statusCode === 429) return "rate_limited";
  if (statusCode && statusCode >= 500) return "provider_failed";
  return "provider_failed";
}

export class AmadeusProviderAdapter implements AccommodationProviderAdapter {
  readonly name = "amadeus" as const;

  /** Search hotels via Amadeus for the provided coordinates and dates. */
  search(
    params: AccommodationSearchParams,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderSearchResult>> {
    return this.execute("search", ctx, async () => {
      if (params.lat === undefined || params.lng === undefined) {
        throw new ProviderError(
          "provider_failed",
          "missing coordinates for Amadeus search",
          {
            provider: this.name,
          }
        );
      }
      const geo = await listHotelsByGeocode({
        latitude: params.lat,
        longitude: params.lng,
        radiusKm: params.maxDistanceKm ?? 5,
      });
      const hotels = amadeusHotelSchema.array().parse(geo.data ?? []);
      if (hotels.length === 0) {
        return { currency: params.currency ?? "USD", listings: [], total: 0 };
      }
      const offersResponse = await searchHotelOffers({
        adults: params.guests ?? 1,
        checkInDate: params.checkin,
        checkOutDate: params.checkout,
        currency: params.currency ?? "USD",
        hotelIds: hotels.map((h) => h.hotelId),
      });
      const offerContainers = amadeusHotelOfferContainerSchema
        .array()
        .parse(offersResponse.data ?? []);
      const offersByHotel = offerContainers.reduce<
        Record<string, (typeof offerContainers)[0]["offers"]>
      >((acc, container) => {
        acc[container.hotel.hotelId] = container.offers ?? [];
        return acc;
      }, {});
      return {
        currency: params.currency ?? "USD",
        listings: mapHotelsToListings(hotels, offersByHotel, {
          checkin: params.checkin,
          checkout: params.checkout,
          guests: params.guests,
        }) as Record<string, unknown>[],
        total: hotels.length,
      };
    });
  }

  /** Fetch hotel details and offers for a listing. */
  getDetails(
    params: AccommodationDetailsParams,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderDetailsResult>> {
    return this.execute("details", ctx, async () => {
      const offers = await searchHotelOffers({
        adults: params.adults ?? 1,
        checkInDate: params.checkin ?? new Date().toISOString().slice(0, 10),
        checkOutDate:
          params.checkout ??
          new Date(Date.now() + 86_400_000).toISOString().slice(0, 10),
        hotelIds: [params.listingId],
      });
      const parsed = amadeusHotelOfferContainerSchema.array().parse(offers.data ?? []);
      const container = parsed[0];
      return {
        listing: {
          hotel: container?.hotel,
          id: params.listingId,
          offers: container?.offers,
          provider: this.name,
        },
      };
    });
  }

  /** Check room availability and get booking token. */
  checkAvailability(
    params: AccommodationCheckAvailabilityParams,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderAvailabilityResult>> {
    return this.execute("checkAvailability", ctx, async () => {
      // Amadeus hotelOffersSearch response already contains final price; reuse as availability lock.
      const offers = await searchHotelOffers({
        adults: params.guests ?? 1,
        checkInDate: params.checkIn,
        checkOutDate: params.checkOut,
        hotelIds: [params.propertyId],
      });
      const parsed = amadeusHotelOfferContainerSchema.array().parse(offers.data ?? []);
      const allOffers = parsed.flatMap((c) => c.offers ?? []);
      const match =
        allOffers.find((offer) => offer.id === params.rateId) ?? allOffers[0];
      if (!match) {
        throw new ProviderError("not_found", "offer not found", {
          provider: this.name,
        });
      }
      return {
        bookingToken: match.id,
        expiresAt: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        price: {
          breakdown: {
            base: match.price.base,
          },
          currency: match.price.currency,
          total: match.price.total,
        },
        propertyId: params.propertyId,
        rateId: match.id,
      };
    });
  }

  /** Create a booking reservation. */
  createBooking(
    payload: ProviderBookingPayload,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderBookingResult>> {
    return this.execute("createBooking", ctx, async () => {
      const response = await bookHotelOffer(payload);
      const booking = amadeusHotelBookingSchema.parse(response.data ?? {});
      return {
        confirmationNumber:
          booking.providerConfirmationId ??
          booking.associatedRecords?.[0]?.reference ??
          booking.id,
        itineraryId: booking.id,
        providerBookingId: booking.id,
      };
    });
  }

  /** Build Amadeus-specific booking payload. */
  buildBookingPayload(
    params: AccommodationBookingRequest,
    options?: { paymentIntentId?: string; currency?: string; totalCents?: number }
  ): ProviderBookingPayload {
    const travelerName = params.guestName.trim().split(/\s+/);
    const givenName = travelerName[0] ?? params.guestName;
    const familyName =
      travelerName.slice(1).join(" ") || travelerName[0] || params.guestName;
    const amountValue =
      options?.totalCents !== undefined
        ? (options.totalCents / 100).toFixed(2)
        : undefined;

    const payments =
      options?.paymentIntentId && options?.currency && amountValue
        ? [
            {
              amount: {
                amount: amountValue,
                currencyCode: options.currency,
              },
              method: "external_prepaid",
              reference: options.paymentIntentId,
              vendorCode: "STRIPE",
            },
          ]
        : [];

    return {
      data: {
        guests: [
          {
            contact: {
              email: params.guestEmail,
              phone: params.guestPhone ?? "",
            },
            id: 1,
            name: { firstName: givenName, lastName: familyName, title: "MR" },
          },
        ],
        hotelOffers: [{ id: params.bookingToken }],
        payments,
        remarks: {
          general: [
            {
              text: `StripePaymentIntent=${options?.paymentIntentId ?? "not-set"}`,
            },
            {
              text: `PrepaidAmount=${amountValue ?? "unknown"} ${
                options?.currency ?? params.currency
              }`,
            },
          ],
        },
        type: "hotel-order",
      },
    };
  }

  /** Execute a provider operation with telemetry and retry semantics. */
  private execute<T>(
    operation: string,
    _ctx: ProviderContext | undefined,
    fn: () => Promise<T>
  ): Promise<ProviderResult<T>> {
    return withTelemetrySpan(
      `provider.amadeus.${operation}`,
      {
        attributes: {
          "provider.name": this.name,
          "provider.operation": operation,
        },
      },
      async (span) => {
        let retries = 0;
        try {
          const result = await retryWithBackoff(fn, {
            attempts: 3,
            baseDelayMs: 200,
            isRetryable: (error) => this.isRetryable(error),
            maxDelayMs: 1_000,
            onRetry: ({ delayMs }) => {
              retries += 1;
              span.addEvent("provider.retry", { attempt: retries, delayMs });
            },
          });
          return { ok: true as const, retries, value: result };
        } catch (error) {
          const statusCode = this.getStatusCode(error);
          const code = mapStatusToProviderCode(statusCode);
          const providerError =
            error instanceof ProviderError
              ? error
              : new ProviderError(code, "amadeus adapter error", {
                  operation,
                  provider: this.name,
                  statusCode,
                });
          span.recordException(providerError);
          return { error: providerError, ok: false as const, retries };
        }
      }
    );
  }

  /** Determines if an error is retryable based on HTTP status codes. */
  private isRetryable(error: unknown): boolean {
    const status = this.getStatusCode(error);
    return status !== undefined && DEFAULT_RETRYABLE_CODES.has(status);
  }

  /** Extract status code from Amadeus SDK error shape. */
  private getStatusCode(error: unknown): number | undefined {
    if (typeof error === "object" && error && "response" in error) {
      return (error as { response?: { statusCode?: number } }).response?.statusCode;
    }
    return undefined;
  }
}
