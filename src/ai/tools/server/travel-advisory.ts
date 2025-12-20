/**
 * @fileoverview Travel advisory and safety scoring tool.
 *
 * Provides safety scores and travel advisories for destinations using
 * US State Department Travel Advisories API with caching (7d TTL).
 * Falls back to stub if API unavailable.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  travelAdvisoryInputSchema,
  travelAdvisoryOutputSchema,
} from "@ai/tools/schemas/travel-advisory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import type { SafetyResult } from "@ai/tools/server/travel-advisory/providers";
import {
  getDefaultProvider,
  registerProvider,
} from "@ai/tools/server/travel-advisory/providers";
import { createStateDepartmentProvider } from "@ai/tools/server/travel-advisory/providers/state-department";
import { mapToCountryCode } from "@ai/tools/server/travel-advisory/utils";
import type { z } from "zod";
import { hashInputForCache } from "@/lib/cache/hash";
import { createServerLogger } from "@/lib/telemetry/logger";

// Initialize and register the State Department provider
const stateDepartmentProvider = createStateDepartmentProvider();
registerProvider(stateDepartmentProvider);

// Create logger first (used in fetchSafetyScores below)
const travelAdvisoryLogger = createServerLogger("tools.travel_advisory", {
  redactKeys: ["error"],
});

/**
 * Fetch safety scores from State Department API or similar service.
 *
 * @param destination Destination name or country code.
 * @param precomputedCountryCode Optional pre-computed country code to avoid redundant mapping.
 * @returns Promise resolving to safety result or null if unavailable.
 */
async function fetchSafetyScores(
  destination: string,
  precomputedCountryCode?: string | null
): Promise<SafetyResult | null> {
  const provider = getDefaultProvider();
  if (!provider) {
    return null;
  }

  // Use pre-computed country code if provided, otherwise map destination
  const countryCode =
    precomputedCountryCode === undefined
      ? mapToCountryCode(destination)
      : precomputedCountryCode;
  if (!countryCode) {
    // If destination doesn't map to a country code, return null
    // (caller will handle fallback)
    return null;
  }

  try {
    const result = await provider.getCountryAdvisory(countryCode);
    if (result) {
      // Update destination to match the input (preserve user's query)
      return {
        ...result,
        destination,
      };
    }
    return null;
  } catch (error) {
    // Log error but don't throw - let caller handle fallback
    travelAdvisoryLogger.error("provider_fetch_failed", {
      countryCode,
      destinationLength: destination.length,
      error: error instanceof Error ? error.message : "unknown_error",
    });
    return null;
  }
}

/**
 * Get travel advisory and safety scores for a destination.
 *
 * Uses US State Department Travel Advisories API with caching (7d TTL).
 * Falls back to stub if API unavailable or country not found.
 *
 * @returns Safety scores and advisory information.
 */

type TravelAdvisoryInput = z.infer<typeof travelAdvisoryInputSchema>;

type TravelAdvisoryResult = z.infer<typeof travelAdvisoryOutputSchema>;

export const getTravelAdvisory = createAiTool<
  TravelAdvisoryInput,
  TravelAdvisoryResult
>({
  description:
    "Get travel advisory and safety scores for a destination using US State Department Travel Advisories API. Accepts country names or ISO country codes (e.g., 'United States', 'US', 'France', 'FR').",
  execute: async (params) => {
    // Validate input at boundary (AI SDK validates, but ensure for direct calls)
    const validatedParams = travelAdvisoryInputSchema.parse(params);
    const mappedCountryCode = mapToCountryCode(validatedParams.destination);
    // Fetch from API (pass pre-computed country code to avoid redundant mapping)
    const result = await fetchSafetyScores(
      validatedParams.destination,
      mappedCountryCode
    );

    if (!result) {
      // Fallback to stub if API unavailable or country not found
      return {
        categories: [],
        destination: validatedParams.destination,
        fromCache: false,
        overallScore: 75,
        provider: "stub",
        summary:
          "Safety information not available. Data provided by U.S. Department of State.",
      } as const;
    }

    return {
      ...result,
      fromCache: false,
    } as const;
  },
  guardrails: {
    cache: {
      key: (params) =>
        `v1:${hashInputForCache(params.destination.trim().toLowerCase())}`,
      namespace: "travel_advisory",
      onHit: (cached) => ({
        ...cached,
        fromCache: true,
      }),
      ttlSeconds: 60 * 60 * 24 * 7,
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      prefix: "ratelimit:tools:travel-advisory",
      window: "1 m",
    },
    telemetry: {
      attributes: (params) => ({
        countryCode: mapToCountryCode(params.destination) ?? "unknown",
        destinationLength: params.destination.length,
      }),
    },
  },
  inputSchema: travelAdvisoryInputSchema,
  name: "getTravelAdvisory",
  outputSchema: travelAdvisoryOutputSchema,
  validateOutput: true,
});
