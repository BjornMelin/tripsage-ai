/**
 * @fileoverview Shared helpers for trips detail UI (formatting, conversions, payload normalization).
 */

import type { ItineraryItem, UiTrip } from "@schemas/trips";
import { DateUtils } from "@/lib/dates/unified-date-utils";

export type BookingStatus = ItineraryItem["bookingStatus"];

export function toDateTimeLocalValue(value: string | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

export function toIsoDateTimeOrUndefined(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const date = new Date(trimmed);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString();
}

export function formatTripDates(trip: UiTrip): string {
  const start = trip.startDate ? DateUtils.parse(trip.startDate) : null;
  const end = trip.endDate ? DateUtils.parse(trip.endDate) : null;
  if (!start || !end) return "Dates not set";
  return `${DateUtils.format(start, "MMM dd, yyyy")} – ${DateUtils.format(end, "MMM dd, yyyy")}`;
}

export function formatItineraryTimestamp(value: string | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function buildPayload(entries: Record<string, string>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const [key, rawValue] of Object.entries(entries)) {
    const value = rawValue.trim();
    if (!value) continue;
    payload[key] = value;
  }
  return payload;
}

export function bookingStatusLabel(status: BookingStatus): string {
  switch (status) {
    case "planned":
      return "Planned";
    case "reserved":
      return "Reserved";
    case "booked":
      return "Booked";
    case "completed":
      return "Completed";
    case "cancelled":
      return "Cancelled";
    default:
      return status;
  }
}

export function coercePayloadToStringRecord(
  payload: Record<string, unknown> | null | undefined
): Record<string, string> {
  if (!payload) return {};
  return Object.fromEntries(
    Object.entries(payload).flatMap(([key, value]) =>
      typeof value === "string" ? ([[key, value]] as const) : []
    )
  );
}
