/**
 * @fileoverview Polyline encoding/decoding utilities for Google Maps Routes.
 *
 * Provides utilities for decoding encoded polylines from Routes API responses
 * for client-side map rendering.
 */

/**
 * Decode an encoded polyline string to an array of [lat, lng] coordinates.
 *
 * Implements the Google Polyline Algorithm Format.
 *
 * @param encoded Encoded polyline string from Routes API.
 * @returns Array of [latitude, longitude] coordinate pairs.
 */
export function decodePolyline(encoded: string): Array<[number, number]> {
  const coordinates: Array<[number, number]> = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte: number;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += deltaLat;

    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += deltaLng;

    coordinates.push([lat / 1e5, lng / 1e5]);
  }

  return coordinates;
}

/**
 * Encode an array of [lat, lng] coordinates to a polyline string.
 *
 * @param coordinates Array of [latitude, longitude] coordinate pairs.
 * @returns Encoded polyline string.
 */
export function encodePolyline(coordinates: Array<[number, number]>): string {
  let encoded = "";
  let prevLat = 0;
  let prevLng = 0;

  for (const [lat, lng] of coordinates) {
    const latDelta = Math.round((lat - prevLat) * 1e5);
    const lngDelta = Math.round((lng - prevLng) * 1e5);

    encoded += encodeValue(latDelta);
    encoded += encodeValue(lngDelta);

    prevLat = lat;
    prevLng = lng;
  }

  return encoded;
}

/**
 * Encode a single delta value for polyline encoding.
 *
 * @param value Delta value to encode.
 * @returns Encoded string segment.
 */
function encodeValue(value: number): string {
  let encodedValue = value < 0 ? ~(value << 1) : value << 1;
  let encoded = "";

  while (encodedValue >= 0x20) {
    encoded += String.fromCharCode((0x20 | (encodedValue & 0x1f)) + 63);
    encodedValue >>= 5;
  }

  encoded += String.fromCharCode((encodedValue & 0x1f) + 63);
  return encoded;
}
