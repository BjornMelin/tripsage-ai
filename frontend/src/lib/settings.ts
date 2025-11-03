/**
 * @fileoverview Frontend settings for provider selection and attribution.
 * Server-only usage for model registry; no secrets exposed client-side.
 */
import "server-only";

import type { ProviderId, ProviderSettings } from "@/lib/providers/types";

const DEFAULT_PREFERENCE: ProviderId[] = ["openai", "openrouter", "anthropic", "xai"];

/**
 * Return provider settings. Values are derived from environment variables
 * where applicable to avoid hardcoding deployment-specific data.
 */
export function getProviderSettings(): ProviderSettings {
  const referer = process.env.OPENROUTER_REFERER;
  const title = process.env.OPENROUTER_TITLE;
  return {
    openrouterAttribution: {
      referer: referer && referer !== "undefined" ? referer : undefined,
      title: title && title !== "undefined" ? title : undefined,
    },
    preference: DEFAULT_PREFERENCE,
  } satisfies ProviderSettings;
}
