/**
 * @fileoverview Zod schemas for Amadeus hotel search, offers, and booking responses.
 */

import { primitiveSchemas } from "@schemas/registry";
import { z } from "zod";

/** Schema for Amadeus address. */
export const amadeusAddressSchema = z.strictObject({
  cityName: z.string().optional(),
  countryCode: z.string().optional(),
  lines: z.array(z.string()).optional(),
  postalCode: z.string().optional(),
});

/** Schema for Amadeus geo. */
export const amadeusGeoSchema = z.strictObject({
  latitude: z.number(),
  longitude: z.number(),
});

/** Schema for Amadeus hotel. */
export const amadeusHotelSchema = z.strictObject({
  address: amadeusAddressSchema.optional(),
  chainCode: z.string().optional(),
  geoCode: amadeusGeoSchema.optional(),
  hotelId: z.string(),
  iataCode: z.string().optional(),
  name: z.string(),
});

/** Type for Amadeus hotel. */
export type AmadeusHotel = z.infer<typeof amadeusHotelSchema>;

/** Schema for Amadeus offer price. */
export const amadeusOfferPriceSchema = z.strictObject({
  base: z.string().optional(),
  currency: primitiveSchemas.isoCurrency,
  taxes: z
    .array(
      z.strictObject({
        amount: z.string(),
        code: z.string().optional(),
        currency: primitiveSchemas.isoCurrency.optional(),
        included: z.boolean().optional(),
      })
    )
    .optional(),
  total: z.string(),
});

/** Schema for Amadeus hotel offer. */
export const amadeusHotelOfferSchema = z.strictObject({
  checkInDate: z.string(),
  checkOutDate: z.string(),
  guests: z
    .strictObject({
      adults: z.number().optional(),
    })
    .optional(),
  id: z.string(),
  policies: z.record(z.string(), z.unknown()).optional(),
  price: amadeusOfferPriceSchema,
  room: z
    .strictObject({
      description: z.strictObject({ text: z.string().optional() }).optional(),
      type: z.string().optional(),
      typeEstimated: z
        .strictObject({
          beds: z.number().optional(),
          bedType: z.string().optional(),
          category: z.string().optional(),
        })
        .optional(),
    })
    .optional(),
});

/** Type for Amadeus hotel offer. */
export type AmadeusHotelOffer = z.infer<typeof amadeusHotelOfferSchema>;

/** Schema for Amadeus hotel offer container. */
export const amadeusHotelOfferContainerSchema = z.strictObject({
  available: z.boolean().optional(),
  hotel: amadeusHotelSchema,
  offers: z.array(amadeusHotelOfferSchema).default([]),
});

/** Type for Amadeus hotel offer container. */
export type AmadeusHotelOfferContainer = z.infer<
  typeof amadeusHotelOfferContainerSchema
>;

/** Schema for Amadeus hotel booking. */
export const amadeusHotelBookingSchema = z.strictObject({
  associatedRecords: z
    .array(
      z.strictObject({
        creationDate: z.string().optional(),
        reference: z.string().optional(),
      })
    )
    .optional(),
  id: z.string().optional(),
  providerConfirmationId: z.string().optional(),
});

/** Type for Amadeus hotel booking. */
export type AmadeusHotelBooking = z.infer<typeof amadeusHotelBookingSchema>;
