/**
 * @fileoverview Placeholder POI lookup tool.
 *
 * Provides a stubbed point-of-interest lookup that returns an empty list.
 * Wired through guardrails so Phase P4 can replace the execute body with a
 * real OpenTripMap integration without changing call sites.
 */

import { tool } from "ai";
import { z } from "zod";

/**
 * Lookup points of interest near a destination or coordinate.
 *
 * Returns a list of POIs with basic metadata. This stub returns an empty
 * array and logs via guardrail telemetry in the surrounding wrapper.
 */
export const lookupPoiContext = tool({
  description: "Lookup points of interest near a destination or coordinate (stub).",
  /**
   * Execute stub POI lookup.
   *
   * @returns An object with `pois` array (always empty in stub) and echo of inputs.
   */
  execute: (params) => {
    return {
      inputs: params,
      pois: [],
      provider: "stub",
    } as const;
  },
  inputSchema: z
    .object({
      destination: z.string().optional(),
      lat: z.number().optional(),
      lon: z.number().optional(),
      radiusMeters: z.number().int().positive().default(1000),
    })
    .refine(
      (o) =>
        Boolean(o.destination) ||
        (typeof o.lat === "number" && typeof o.lon === "number"),
      { message: "Provide destination or lat/lon" }
    ),
});
