/**
 * @fileoverview Cache invalidation webhook handler for database changes.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { errorResponse, unauthorizedResponse } from "@/lib/api/route-helpers";
import { bumpTags } from "@/lib/cache/tags";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { parseAndVerify } from "@/lib/webhooks/payload";

/**
 * Returns cache tags to invalidate for a given database table.
 *
 * @param table - The name of the database table that changed.
 * @return Array of cache tag names to invalidate.
 */
function tagsForTable(table: string): string[] {
  switch (table) {
    case "trips":
      return ["trip", "user_trips", "trip_search", "search", "search_cache"];
    case "flights":
      return ["flight", "flight_search", "search", "search_cache"];
    case "accommodations":
      return ["accommodation", "hotel_search", "search", "search_cache"];
    case "search_destinations":
    case "search_flights":
    case "search_hotels":
    case "search_activities":
      return ["search", "search_cache"];
    case "trip_collaborators":
      return ["trips", "users", "search"];
    case "chat_messages":
    case "chat_sessions":
      return ["memory", "conversation", "chat_memory"];
    default:
      return ["search", "cache"];
  }
}

/**
 * Handles database change webhooks to invalidate related cache tags.
 *
 * @param req - The incoming webhook request.
 * @return Response indicating success or error.
 */
export async function POST(req: NextRequest) {
  return await withTelemetrySpan(
    "webhook.cache",
    { attributes: { route: "/api/hooks/cache" } },
    async (span) => {
      const { ok, payload } = await parseAndVerify(req);
      if (!ok || !payload) {
        return unauthorizedResponse();
      }
      if (!payload.table) {
        return errorResponse({
          error: "invalid_request",
          reason: "Missing table in webhook payload",
          status: 400,
        });
      }
      span.setAttribute("table", payload.table);
      span.setAttribute("op", payload.type);
      const tags = tagsForTable(payload.table);
      const bumped = await bumpTags(tags);
      span.setAttribute("tags.count", tags.length);
      return NextResponse.json({ bumped, ok: true });
    }
  );
}
