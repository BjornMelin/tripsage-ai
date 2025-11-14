/**
 * @fileoverview Provider abstraction for travel advisory APIs.
 *
 * Defines the interface for travel advisory providers, enabling
 * multiple data sources (State Department, GeoSure, etc.) with
 * a unified API.
 */

/**
 * Safety score category structure.
 */
export type SafetyCategory = {
  category: string;
  value: number;
  description?: string;
};

/**
 * Safety score result structure.
 */
export type SafetyResult = {
  destination: string;
  overallScore: number;
  categories: SafetyCategory[];
  summary?: string;
  lastUpdated?: string;
  provider: string;
  sourceUrl?: string;
};

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
   * @param countryCode - Two-letter ISO country code (e.g., "US", "FR").
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
 * @param provider - Provider implementation to register.
 */
export function registerProvider(provider: AdvisoryProvider): void {
  providerRegistry.set(provider.getProviderName(), provider);
}

/**
 * Get a registered provider by name.
 *
 * @param name - Provider name.
 * @returns Provider instance or undefined if not found.
 */
export function getProvider(name: string): AdvisoryProvider | undefined {
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
