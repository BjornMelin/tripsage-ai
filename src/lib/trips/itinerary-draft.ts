/**
 * @fileoverview Draft helpers for the trip itinerary item dialog.
 */

import type { ItineraryItem, ItineraryItemType } from "@schemas/trips";
import {
  type BookingStatus,
  coercePayloadToStringRecord,
  toDateTimeLocalValue,
} from "@/lib/trips/trip-detail-utils";

export type ItineraryDraft = {
  id?: number;
  itemType: ItineraryItemType;
  title: string;
  description: string;
  location: string;
  bookingStatus: BookingStatus;
  startAtLocal: string;
  endAtLocal: string;
  price: string;
  currency: string;
  payload: Record<string, string>;
};

export const DEFAULT_ITINERARY_DRAFT: ItineraryDraft = {
  bookingStatus: "planned",
  currency: "USD",
  description: "",
  endAtLocal: "",
  itemType: "activity",
  location: "",
  payload: {},
  price: "",
  startAtLocal: "",
  title: "",
};

export function itineraryDraftFromItem(item: ItineraryItem): ItineraryDraft {
  return {
    bookingStatus: item.bookingStatus,
    currency: item.currency,
    description: item.description ?? "",
    endAtLocal: toDateTimeLocalValue(item.endAt),
    id: item.id,
    itemType: item.itemType,
    location: item.location ?? "",
    payload: coercePayloadToStringRecord(item.payload),
    price: item.price !== undefined ? String(item.price) : "",
    startAtLocal: toDateTimeLocalValue(item.startAt),
    title: item.title,
  };
}
