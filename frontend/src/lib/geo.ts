/**
 * @fileoverview Geographic distance calculation utilities.
 */

/** Earth's radius in kilometers. */
const EARTH_RADIUS_KM = 6371;

/** Coordinates interface. */
export interface Coordinates {
  lat: number;
  lng: number;
}

/**
 * Calculates the great-circle distance between two points using the Haversine formula.
 *
 * @param from - Origin coordinates.
 * @param to - Destination coordinates.
 * @returns Distance in kilometers.
 */
export function calculateDistanceKm(from: Coordinates, to: Coordinates): number {
  const lat1Rad = (from.lat * Math.PI) / 180;
  const lat2Rad = (to.lat * Math.PI) / 180;
  const deltaLat = ((to.lat - from.lat) * Math.PI) / 180;
  const deltaLng = ((to.lng - from.lng) * Math.PI) / 180;

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1Rad) *
      Math.cos(lat2Rad) *
      Math.sin(deltaLng / 2) *
      Math.sin(deltaLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return EARTH_RADIUS_KM * c;
}
