/**
 * @fileoverview Shared helpers for the dashboard “Plan New Trip” flow.
 */

import { ISO_DATE_STRING } from "@schemas/shared/time";
import type { TripCreateInput, TripSuggestion } from "@schemas/trips";
import { z } from "zod";
import { DateUtils } from "@/lib/dates/unified-date-utils";

const OPTIONAL_ISO_DATE_STRING = z.union([ISO_DATE_STRING, z.literal("")]).optional();

export const PLAN_TRIP_FORM_SCHEMA = z
  .strictObject({
    description: z.string().max(1000, { error: "Notes too long" }).optional(),
    destination: z
      .string()
      .min(1, { error: "Destination is required" })
      .max(200, { error: "Destination too long" }),
    endDate: OPTIONAL_ISO_DATE_STRING,
    startDate: OPTIONAL_ISO_DATE_STRING,
    title: z.string().max(200, { error: "Title too long" }).optional(),
  })
  .refine(
    (value) => {
      if (!value.startDate || !value.endDate) return true;
      // YYYY-MM-DD sorts lexicographically in chronological order.
      return value.endDate >= value.startDate;
    },
    { error: "End date must be on or after start date", path: ["endDate"] }
  );

export type PlanTripFormData = z.infer<typeof PLAN_TRIP_FORM_SCHEMA>;

export function computeDefaultTripDates(now: Date): {
  startDate: string;
  endDate: string;
} {
  const start = DateUtils.add(now, 1, "days");
  const end = DateUtils.add(start, 7, "days");
  return {
    endDate: DateUtils.format(end, "yyyy-MM-dd"),
    startDate: DateUtils.format(start, "yyyy-MM-dd"),
  };
}

export function computeDefaultTripTitle(destination: string): string {
  const clean = destination.trim();
  if (!clean) return "New Trip";
  return `Trip to ${clean}`;
}

function isoDateToIsoDateTime(value: string): string {
  return DateUtils.formatForApi(DateUtils.parse(value));
}

export function makeCreateTripPayload(
  values: PlanTripFormData,
  defaults: { startDate: string; endDate: string },
  suggestion: TripSuggestion | null
): TripCreateInput {
  const destination = values.destination.trim();
  const title =
    values.title?.trim() ||
    suggestion?.title?.trim() ||
    computeDefaultTripTitle(destination);

  const durationDays =
    suggestion?.duration && suggestion.duration > 0 ? suggestion.duration : 7;
  const requestedStartIsoDate = values.startDate?.trim() ?? "";
  const requestedEndIsoDate = values.endDate?.trim() ?? "";

  let startIsoDate = requestedStartIsoDate || defaults.startDate;
  let endIsoDate = requestedEndIsoDate;

  if (!endIsoDate) {
    endIsoDate = DateUtils.format(
      DateUtils.add(DateUtils.parse(startIsoDate), durationDays, "days"),
      "yyyy-MM-dd"
    );
  }

  if (!requestedStartIsoDate && requestedEndIsoDate) {
    startIsoDate = DateUtils.format(
      DateUtils.subtract(DateUtils.parse(requestedEndIsoDate), durationDays, "days"),
      "yyyy-MM-dd"
    );
    endIsoDate = requestedEndIsoDate;
  }

  const startDate = isoDateToIsoDateTime(startIsoDate);
  const endDate = isoDateToIsoDateTime(endIsoDate);
  const description =
    values.description?.trim() || suggestion?.description?.trim() || undefined;

  return {
    currency: suggestion?.currency ?? "USD",
    description,
    destination,
    endDate,
    startDate,
    status: "planning",
    title,
    travelers: 1,
    tripType: "leisure",
    visibility: "private",
  };
}
