/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { type Coordinates, calculateDistanceKm } from "../geo";

describe("calculateDistanceKm", () => {
  it("returns 0 for identical coordinates", () => {
    const point: Coordinates = { lat: 48.8566, lng: 2.3522 };
    expect(calculateDistanceKm(point, point)).toBe(0);
  });

  it("calculates distance between Paris and London (~344 km)", () => {
    const paris: Coordinates = { lat: 48.8566, lng: 2.3522 };
    const london: Coordinates = { lat: 51.5074, lng: -0.1278 };
    const distance = calculateDistanceKm(paris, london);
    // Known distance is ~344 km, allow small variance for formula precision
    expect(distance).toBeGreaterThan(340);
    expect(distance).toBeLessThan(350);
  });

  it("calculates distance between New York and Los Angeles (~3940 km)", () => {
    const newYork: Coordinates = { lat: 40.7128, lng: -74.006 };
    const losAngeles: Coordinates = { lat: 34.0522, lng: -118.2437 };
    const distance = calculateDistanceKm(newYork, losAngeles);
    expect(distance).toBeGreaterThan(3900);
    expect(distance).toBeLessThan(4000);
  });

  it("handles coordinates crossing the prime meridian", () => {
    const east: Coordinates = { lat: 51.5, lng: 10 };
    const west: Coordinates = { lat: 51.5, lng: -10 };
    const distance = calculateDistanceKm(east, west);
    // ~1400 km along same latitude crossing 20° longitude
    expect(distance).toBeGreaterThan(1300);
    expect(distance).toBeLessThan(1500);
  });

  it("handles coordinates crossing the equator", () => {
    const north: Coordinates = { lat: 10, lng: 0 };
    const south: Coordinates = { lat: -10, lng: 0 };
    const distance = calculateDistanceKm(north, south);
    // 20° latitude difference ≈ 2220 km
    expect(distance).toBeGreaterThan(2200);
    expect(distance).toBeLessThan(2250);
  });

  it("is commutative (A→B equals B→A)", () => {
    const a: Coordinates = { lat: 35.6762, lng: 139.6503 }; // Tokyo
    const b: Coordinates = { lat: -33.8688, lng: 151.2093 }; // Sydney
    expect(calculateDistanceKm(a, b)).toBeCloseTo(calculateDistanceKm(b, a), 10);
  });
});
