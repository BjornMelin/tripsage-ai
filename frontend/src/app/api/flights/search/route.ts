/**
 * @fileoverview Flight search API route.
 *
 * POST /api/flights/search
 * Searches for flights using Duffel provider.
 */

import "server-only";

import { searchFlightsService } from "@domain/flights/service";
import { flightSearchRequestSchema } from "@schemas/flights";
import { withApiGuards } from "@/lib/api/factory";

export const POST = withApiGuards({
  auth: false, // Allow anonymous searches
  rateLimit: "flights:search",
  schema: flightSearchRequestSchema,
  telemetry: "flights.search",
})(async (_req, _ctx, body) => {
  const result = await searchFlightsService(body);

  return Response.json(result);
});
