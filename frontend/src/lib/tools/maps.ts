/**
 * @fileoverview Google Maps tools: geocode, distance matrix (basic variants).
 */

import { tool } from "ai";
import { z } from "zod";

const GMAPS_KEY = process.env.GOOGLE_MAPS_API_KEY;

export const geocode = tool({
  description: "Geocode a location using Google Maps Geocoding API.",
  execute: async ({ address }) => {
    if (!GMAPS_KEY) throw new Error("gmaps_not_configured");
    const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
    url.searchParams.set("address", address);
    url.searchParams.set("key", GMAPS_KEY);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`gmaps_failed:${res.status}`);
    const data = await res.json();
    return data?.results ?? [];
  },
  inputSchema: z.object({ address: z.string().min(2) }),
});

export const distanceMatrix = tool({
  description:
    "Compute distances between origins and destinations via Google Distance Matrix.",
  execute: async ({ origins, destinations, units }) => {
    if (!GMAPS_KEY) throw new Error("gmaps_not_configured");
    const url = new URL("https://maps.googleapis.com/maps/api/distancematrix/json");
    url.searchParams.set("origins", origins.join("|"));
    url.searchParams.set("destinations", destinations.join("|"));
    url.searchParams.set("units", units);
    url.searchParams.set("key", GMAPS_KEY);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`gmaps_dm_failed:${res.status}`);
    return await res.json();
  },
  inputSchema: z.object({
    destinations: z.array(z.string().min(2)).min(1),
    origins: z.array(z.string().min(2)).min(1),
    units: z.enum(["metric", "imperial"]).default("metric"),
  }),
});
