/**
 * @fileoverview Shared place id normalization helpers for trips.
 */

export function normalizePlaceIdForStorage(placeId: string): string {
  return placeId.startsWith("places/") ? placeId.slice("places/".length) : placeId;
}
