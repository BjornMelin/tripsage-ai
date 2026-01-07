/**
 * @fileoverview Trip tools (saved places persistence).
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  createToolError,
  isToolError,
  TOOL_ERROR_CODES,
} from "@ai/tools/server/errors";
import type {
  SavePlaceToTripToolInput,
  SavePlaceToTripToolOutput,
} from "@schemas/places";
import {
  savePlaceToTripToolInputSchema,
  savePlaceToTripToolOutputSchema,
} from "@schemas/places";
import { nowIso } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { normalizePlaceIdForStorage } from "@/lib/trips/place-id";

const logger = createServerLogger("tools.trips");

export const savePlaceToTrip = createAiTool<
  SavePlaceToTripToolInput,
  SavePlaceToTripToolOutput
>({
  description: "Save a place to a trip so it can be used in planning and itineraries.",
  execute: async (args) => {
    try {
      const supabase = await createServerSupabase();
      const { data: auth } = await supabase.auth.getUser();
      const sessionUserId = auth?.user?.id;

      if (!sessionUserId || sessionUserId !== args.userId) {
        throw createToolError(
          TOOL_ERROR_CODES.tripSavePlaceUnauthorized,
          "Unauthorized",
          {
            reason: "session_user_mismatch",
          }
        );
      }

      const placeId = normalizePlaceIdForStorage(args.place.placeId);
      const snapshot = {
        place: {
          ...args.place,
          placeId,
        },
        savedAt: nowIso(),
      };

      const { error } = await supabase.from("saved_places").upsert(
        {
          // biome-ignore lint/style/useNamingConvention: database columns
          place_id: placeId,
          // biome-ignore lint/style/useNamingConvention: database columns
          place_snapshot: snapshot,
          // biome-ignore lint/style/useNamingConvention: database columns
          trip_id: args.tripId,
          // biome-ignore lint/style/useNamingConvention: database columns
          user_id: sessionUserId,
        },
        { onConflict: "trip_id,place_id" }
      );

      if (error) {
        logger.warn("tool_trips_save_place_failed", {
          code: (error as { code?: unknown }).code ?? null,
          message: error.message,
          tripId: args.tripId,
        });
        throw createToolError(
          TOOL_ERROR_CODES.tripSavePlaceFailed,
          "Failed to save place",
          {
            code: (error as { code?: unknown }).code ?? null,
          }
        );
      }

      return savePlaceToTripToolOutputSchema.parse(snapshot);
    } catch (err) {
      if (isToolError(err)) {
        throw err;
      }
      const message = err instanceof Error ? err.message : "unknown_error";
      throw createToolError(TOOL_ERROR_CODES.tripSavePlaceFailed, message);
    }
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      prefix: "ratelimit:agent:trips:save_place",
      window: "1 m",
    },
    telemetry: {
      attributes: (args) => ({
        provider: "googleplaces",
        tripId: args.tripId,
      }),
    },
  },
  inputSchema: savePlaceToTripToolInputSchema,
  name: "trips.savePlace",
  outputSchema: savePlaceToTripToolOutputSchema,
  toModelOutput: (result) => ({
    name: result.place.name,
    placeId: result.place.placeId,
    savedAt: result.savedAt,
  }),
  validateOutput: true,
});
