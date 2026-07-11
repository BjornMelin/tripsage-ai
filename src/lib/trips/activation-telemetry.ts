/**
 * @fileoverview Privacy-safe activation telemetry for durable trip mutations.
 */

import "server-only";

import type { ItineraryItemType } from "@schemas/trips";
import { hashTelemetryIdentifier } from "@/lib/telemetry/identifiers";
import {
  recordTelemetryEvent,
  type TelemetrySpanAttributes,
} from "@/lib/telemetry/span";

type ActivationIdentifiers = {
  tripId: number;
  userId: string;
};

type ItineraryCompletionInput = ActivationIdentifiers & {
  itemType: ItineraryItemType;
  operation: "create" | "update";
};

function activationIdentifierAttributes({
  tripId,
  userId,
}: ActivationIdentifiers): TelemetrySpanAttributes {
  const userIdHash = hashTelemetryIdentifier(userId);
  const tripIdHash = hashTelemetryIdentifier(`trip:${tripId}`);

  return {
    ...(tripIdHash ? { "trip.id_hash": tripIdHash } : {}),
    ...(userIdHash ? { "user.id_hash": userIdHash } : {}),
  };
}

function recordActivationEvent(
  eventName: "activation.itinerary_item_completed" | "activation.trip_created",
  attributes: () => TelemetrySpanAttributes
): void {
  try {
    recordTelemetryEvent(eventName, { attributes: attributes() });
  } catch {
    // Persistence has already succeeded; telemetry must never change the result.
  }
}

/** Records a successfully persisted and validated trip creation. */
export function recordTripCreatedActivation(input: ActivationIdentifiers): void {
  recordActivationEvent("activation.trip_created", () =>
    activationIdentifierAttributes(input)
  );
}

/** Records a successfully persisted itinerary item that is now completed. */
export function recordItineraryItemCompletedActivation(
  input: ItineraryCompletionInput
): void {
  recordActivationEvent("activation.itinerary_item_completed", () => ({
    ...activationIdentifierAttributes(input),
    "itinerary.item_type": input.itemType,
    "itinerary.operation": input.operation,
  }));
}
