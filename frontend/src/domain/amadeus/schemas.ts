/**
 * @fileoverview Zod schemas for Amadeus hotel search, offers, and booking responses.
 */

import { z } from "zod";
import { primitiveSchemas } from "@schemas/registry";

/** Schema for Amadeus address. */
export const amadeusAddressSchema = z.strictObject({
  lines: z.array(z.string()).optional(),
  cityName: z.string().optional(),
  postalCode: z.string().optional(),
  countryCode: z.string().optional(),
});

/** Schema for Amadeus geo. */
export const amadeusGeoSchema = z.strictObject({
  latitude: z.number(),
  longitude: z.number(),
});

/** Schema for Amadeus hotel. */
export const amadeusHotelSchema = z.strictObject({
  hotelId: z.string(),
  name: z.string(),
  address: amadeusAddressSchema.optional(),
  geoCode: amadeusGeoSchema.optional(),
  chainCode: z.string().optional(),
  iataCode: z.string().optional(),
});

/** Type for Amadeus hotel. */
export type AmadeusHotel = z.infer<typeof amadeusHotelSchema>;

/** Schema for Amadeus offer price. */
export const amadeusOfferPriceSchema = z.strictObject({
  currency: primitiveSchemas.isoCurrency,
  total: z.string(),
  base: z.string().optional(),
  taxes: z
    .array(
      z.strictObject({
        amount: z.string(),
        currency: primitiveSchemas.isoCurrency.optional(),
        code: z.string().optional(),
        included: z.boolean().optional(),
      })
    )
    .optional(),
});

/** Schema for Amadeus hotel offer. */
export const amadeusHotelOfferSchema = z.strictObject({
  id: z.string(),
  checkInDate: z.string(),
  checkOutDate: z.string(),
  room: z
    .strictObject({
      description: z.strictObject({ text: z.string().optional() }).optional(),
      type: z.string().optional(),
      typeEstimated: z
        .strictObject({
          category: z.string().optional(),
          beds: z.number().optional(),
          bedType: z.string().optional(),
        })
        .optional(),
    })
    .optional(),
  guests: z
    .strictObject({
      adults: z.number().optional(),
    })
    .optional(),
  price: amadeusOfferPriceSchema,
  policies: z.record(z.string(), z.unknown()).optional(),
});

/** Type for Amadeus hotel offer. */
export type AmadeusHotelOffer = z.infer<typeof amadeusHotelOfferSchema>;

/** Schema for Amadeus hotel offer container. */
export const amadeusHotelOfferContainerSchema = z.strictObject({
  hotel: amadeusHotelSchema,
  available: z.boolean().optional(),
  offers: z.array(amadeusHotelOfferSchema).default([]),
});

/** Type for Amadeus hotel offer container. */
export type AmadeusHotelOfferContainer = z.infer<
  typeof amadeusHotelOfferContainerSchema
>;

/** Schema for Amadeus hotel booking. */
export const amadeusHotelBookingSchema = z.strictObject({
  id: z.string().optional(),
  providerConfirmationId: z.string().optional(),
  associatedRecords: z
    .array(
      z.strictObject({
        reference: z.string().optional(),
        creationDate: z.string().optional(),
      })
    )
    .optional(),
});

/** Type for Amadeus hotel booking. */
export type AmadeusHotelBooking = z.infer<typeof amadeusHotelBookingSchema>;
