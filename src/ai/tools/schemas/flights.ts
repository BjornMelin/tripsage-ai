/**
 * @fileoverview Flight tool model output schemas.
 */

import { z } from "zod";

// ===== MODEL OUTPUT SCHEMAS =====

/** Segment within a flight itinerary for model consumption. */
const flightSegmentModelOutputSchema = z.strictObject({
  carrier: z.string().optional(),
  departure: z.string().optional(),
  destination: z.string(),
  flightNumber: z.string().optional(),
  origin: z.string(),
});

/** Itinerary entry for model consumption. */
const flightItineraryModelOutputSchema = z.strictObject({
  id: z.string(),
  price: z.number(),
  segments: z.array(flightSegmentModelOutputSchema),
});

/** Slice within an offer for model consumption. */
const flightSliceModelOutputSchema = z.strictObject({
  cabinClass: z.string(),
  segmentCount: z.number().int(),
  segments: z.array(
    z.strictObject({
      carrier: z.string().optional(),
      departureTime: z.string().optional(),
      destination: z.string(),
      flightNumber: z.string().optional(),
      origin: z.string(),
    })
  ),
});

/** Offer entry for model consumption. */
const flightOfferModelOutputSchema = z.strictObject({
  id: z.string(),
  price: z.number(),
  provider: z.string(),
  slices: z.array(flightSliceModelOutputSchema),
});

/** Flight search result output schema for model consumption. */
export const flightModelOutputSchema = z.strictObject({
  currency: z.string(),
  fromCache: z.boolean(),
  itineraries: z.array(flightItineraryModelOutputSchema),
  itineraryCount: z.number().int(),
  offerCount: z.number().int(),
  offers: z.array(flightOfferModelOutputSchema),
  provider: z.string(),
});

export type FlightModelOutput = z.infer<typeof flightModelOutputSchema>;
