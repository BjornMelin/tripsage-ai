/**
 * @fileoverview Travel advisory and safety scoring tool.
 *
 * Provides safety scores and travel advisories for destinations using
 * US State Department Travel Advisories API with caching (7d TTL).
 * Falls back to stub if API unavailable.
 */

import "server-only";

import { travelAdvisoryInputSchema } from "@ai/tools/schemas/travel-advisory";
import type { SafetyResult } from "@ai/tools/server/travel-advisory/providers";
import {
  getDefaultProvider,
  registerProvider,
} from "@ai/tools/server/travel-advisory/providers";
import { createStateDepartmentProvider } from "@ai/tools/server/travel-advisory/providers/state-department";
import { mapToCountryCode } from "@ai/tools/server/travel-advisory/utils";
import type { ToolCallOptions } from "ai";
import { tool } from "ai";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

// Initialize and register the State Department provider
const stateDepartmentProvider = createStateDepartmentProvider();
registerProvider(stateDepartmentProvider);

/**
 * Fetch safety scores from State Department API or similar service.
 *
 * @param destination Destination name or country code.
 * @returns Promise resolving to safety result or null if unavailable.
 */
async function fetchSafetyScores(destination: string): Promise<SafetyResult | null> {
  const provider = getDefaultProvider();
  if (!provider) {
    return null;
  }

  // Try to map destination to country code
  const countryCode = mapToCountryCode(destination);
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
      destination,
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

export const getTravelAdvisory = tool({
  description:
    "Get travel advisory and safety scores for a destination using US State Department Travel Advisories API. Accepts country names or ISO country codes (e.g., 'United States', 'US', 'France', 'FR').",
  execute: async (params, _callOptions?: ToolCallOptions) => {
    // Validate input at boundary (AI SDK validates, but ensure for direct calls)
    const validatedParams = travelAdvisoryInputSchema.parse(params);
    return await withTelemetrySpan(
      "tool.travel_advisory.get",
      {
        attributes: {
          destination: params.destination,
          "tool.name": "getTravelAdvisory",
        },
      },
      async () => {
        const cacheKey = `travel_advisory:${validatedParams.destination.toLowerCase()}`;

        // Check cache (7d = 604800 seconds)
        const cached = await getCachedJson<SafetyResult>(cacheKey);
        if (cached) {
          return {
            ...cached,
            fromCache: true,
          } as const;
        }

        // Fetch from API
        const result = await fetchSafetyScores(validatedParams.destination);

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

        // Cache results (7d = 604800 seconds)
        await setCachedJson(cacheKey, result, 604800);

        return {
          ...result,
          fromCache: false,
        } as const;
      }
    );
  },
  inputSchema: travelAdvisoryInputSchema,
});
const travelAdvisoryLogger = createServerLogger("tools.travel_advisory");
