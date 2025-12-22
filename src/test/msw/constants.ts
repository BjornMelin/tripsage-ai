/**
 * @fileoverview Shared MSW test constants (determinism + safety).
 */

export const MSW_FIXED_ISO_DATE = "2024-01-01T00:00:00.000Z" as const;

// OpenAI `created` is typically a Unix timestamp in seconds.
export const MSW_FIXED_UNIX_SECONDS = 1_704_067_200 as const; // 2024-01-01T00:00:00Z

export const MSW_SUPABASE_URL = "http://localhost:54321" as const;
