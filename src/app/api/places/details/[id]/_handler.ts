/**
 * @fileoverview Pure handler for Places Details (canonical Places service).
 */

import "server-only";

import type { PlacesDetailsRequest } from "@schemas/api";
import { NextResponse } from "next/server";
import { z } from "zod";
import {
  createPlacesService,
  type PlacesService,
  PlacesServiceError,
} from "@/features/search/server/places/places-service";
import { errorResponse } from "@/lib/api/route-helpers";

export type PlaceDetailsDeps = {
  apiKey: string;
};

export async function handlePlaceDetails(
  deps: PlaceDetailsDeps,
  input: { placeId: string; query: PlacesDetailsRequest }
): Promise<Response> {
  try {
    const service: PlacesService = createPlacesService({ apiKey: deps.apiKey });
    const details = await service.getPlaceDetails({
      placeId: input.placeId,
      sessionToken: input.query.sessionToken,
    });

    return NextResponse.json(details);
  } catch (error) {
    if (error instanceof z.ZodError) {
      return errorResponse({
        err: error,
        error: "invalid_request",
        issues: error.issues,
        reason: "Request validation failed",
        status: 400,
      });
    }

    if (error instanceof PlacesServiceError) {
      return errorResponse({
        err: error,
        error: error.code,
        reason: error.message,
        status: error.status,
      });
    }

    throw error;
  }
}
