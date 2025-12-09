/**
 * @fileoverview Provider abstraction for travel advisory APIs.
 *
 * Defines the interface for travel advisory providers, enabling
 * multiple data sources (State Department, GeoSure, etc.) with
 * a unified API.
 */

import type { SafetyCategory, SafetyResult } from "@ai/tools/schemas/tools";

// Re-export types from schemas for convenience.
export type { SafetyCategory, SafetyResult };

/**
 * Interface for travel advisory providers.
 *
 * Providers implement this interface to supply travel safety
 * data from various sources (government APIs, commercial services, etc.).
 */
export interface AdvisoryProvider {
  /**
   * Get travel advisory for a country by ISO-3166-1 alpha-2 code.
   *
   * @param countryCode Two-letter ISO country code (for example, "US", "FR").
   * @returns Promise resolving to safety result or null if not found.
   */
  getCountryAdvisory(countryCode: string): Promise<SafetyResult | null>;

  /**
   * Get provider name for attribution.
   *
   * @returns Provider identifier string.
   */
  getProviderName(): string;
}

/**
 * Registry of available advisory providers.
 *
 * Maps provider names to their implementations. Used for
 * provider selection and fallback logic.
 */
export const providerRegistry = new Map<string, AdvisoryProvider>();

/**
 * Register an advisory provider.
 *
 * @param provider Provider implementation to register.
 */
export function registerProvider(provider: AdvisoryProvider): void {
  providerRegistry.set(provider.getProviderName(), provider);
}

/**
 * Get a registered provider by name.
 *
 * @param name Provider name.
 * @returns Provider instance or undefined if not found.
 */
export function getProvider(name: string): AdvisoryProvider | undefined {
  if (!name) {
    return undefined;
  }
  return providerRegistry.get(name);
}

/**
 * Get the default provider (State Department).
 *
 * @returns Default provider instance or undefined if not registered.
 */
export function getDefaultProvider(): AdvisoryProvider | undefined {
  return providerRegistry.get("state_department");
}
