/**
 * @fileoverview Pure handler for Places Text Search (canonical Places service).
 */

import "server-only";

import type { PlacesSearchRequest } from "@schemas/api";
import { NextResponse } from "next/server";
import { z } from "zod";
import {
  createPlacesService,
  type PlacesService,
  PlacesServiceError,
} from "@/features/search/server/places/places-service";
import { errorResponse } from "@/lib/api/route-helpers";

export type PlacesSearchDeps = {
  apiKey: string;
  cacheTtlSeconds?: number;
};

export async function handlePlacesSearch(
  deps: PlacesSearchDeps,
  body: PlacesSearchRequest
): Promise<Response> {
  try {
    const service: PlacesService = createPlacesService({
      apiKey: deps.apiKey,
      cacheTtlSeconds: deps.cacheTtlSeconds,
    });

    const result = await service.searchPlaces({
      locationBias: body.locationBias,
      maxResults: body.maxResultCount,
      query: body.textQuery,
    });

    return NextResponse.json(result);
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
