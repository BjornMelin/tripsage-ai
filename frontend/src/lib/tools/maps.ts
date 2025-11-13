/**
 * @fileoverview Google Maps tools: geocode, distance matrix (basic variants).
 */

import "server-only";

import { tool } from "ai";
import { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

// Lazy env access: do not read at module load to avoid test-time validation.
function getGmapsKeyOrNull(): string | null {
  try {
    const key = getGoogleMapsServerKey();
    return key || null;
  } catch {
    return null;
  }
}

/**
 * Zod input schema for geocode tool.
 *
 * Exported for use in guardrails validation and cache key generation.
 */
export const geocodeInputSchema = z.object({ address: z.string().min(2) });

/**
 * Zod input schema for distance matrix tool.
 *
 * Exported for use in guardrails validation and cache key generation.
 */
export const distanceMatrixInputSchema = z.object({
  destinations: z.array(z.string().min(2)).min(1),
  origins: z.array(z.string().min(2)).min(1),
  units: z.enum(["metric", "imperial"]).default("metric"),
});

export const geocode = tool({
  description: "Geocode a location using Google Maps Geocoding API.",
  execute: async ({ address }) =>
    withTelemetrySpan(
      "tool.maps.geocode",
      { attributes: { address, "tool.name": "geocode" }, redactKeys: ["address"] },
      async (span) => {
        const key = getGmapsKeyOrNull();
        if (!key) throw new Error("gmaps_not_configured");
        const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
        url.searchParams.set("address", address);
        url.searchParams.set("key", key);
        span.addEvent("http_get", { url: url.origin + url.pathname });
        const res = await fetch(url);
        if (!res.ok) throw new Error(`gmaps_failed:${res.status}`);
        const data = await res.json();
        return data?.results ?? [];
      }
    ),
  inputSchema: geocodeInputSchema,
});

export const distanceMatrix = tool({
  description:
    "Compute distances between origins and destinations via Google Distance Matrix.",
  execute: async ({ origins, destinations, units }) =>
    withTelemetrySpan(
      "tool.maps.distance_matrix",
      {
        attributes: {
          destinations: destinations.length,
          origins: origins.length,
          "tool.name": "distanceMatrix",
          units,
        },
      },
      async (span) => {
        const key = getGmapsKeyOrNull();
        if (!key) throw new Error("gmaps_not_configured");
        const url = new URL("https://maps.googleapis.com/maps/api/distancematrix/json");
        url.searchParams.set("origins", origins.join("|"));
        url.searchParams.set("destinations", destinations.join("|"));
        url.searchParams.set("units", units);
        url.searchParams.set("key", key);
        span.addEvent("http_get", { url: url.origin + url.pathname });
        const res = await fetch(url);
        if (!res.ok) throw new Error(`gmaps_dm_failed:${res.status}`);
        return await res.json();
      }
    ),
  inputSchema: distanceMatrixInputSchema,
});
