/**
 * @fileoverview Shared trip date parsing helper with consistent error handling.
 */

import { DateUtils } from "@/lib/dates/unified-date-utils";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

type TripDateParseTelemetry = {
  action?: string;
  context?: string;
};

export function parseTripDate(
  value?: string | null,
  telemetry?: TripDateParseTelemetry
): Date | null {
  if (!value) return null;
  try {
    return DateUtils.parse(value);
  } catch (error) {
    recordClientErrorOnActiveSpan(
      error instanceof Error ? error : new Error(String(error)),
      {
        action: telemetry?.action ?? "parseTripDate",
        context: telemetry?.context ?? "parseTripDate",
        value,
      }
    );
    return null;
  }
}
