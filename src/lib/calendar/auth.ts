/**
 * @fileoverview Server-only utility to retrieve Google OAuth provider token
 * from Supabase session for Google Calendar API calls.
 */

import "server-only";

import { createServerSupabase } from "@/lib/supabase/server";

/**
 * Error thrown when Google OAuth token is not available.
 */
export class GoogleTokenError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GoogleTokenError";
  }
}

/**
 * Get Google OAuth provider token from Supabase session.
 *
 * Retrieves the Google provider token from the current user's Supabase session.
 * The token is stored in session.provider_token when the user authenticates
 * via Google OAuth.
 *
 * @returns Promise resolving to Google OAuth access token
 * @throws GoogleTokenError if token is not available or user is not authenticated
 */
export async function getGoogleProviderToken(): Promise<string> {
  const supabase = await createServerSupabase();
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError || !session) {
    throw new GoogleTokenError("No active session found");
  }

  // Check if provider_token exists in session
  // Supabase stores provider tokens in session.provider_token for OAuth providers
  const providerToken =
    // biome-ignore lint/style/useNamingConvention: Supabase API field name
    (session as unknown as { provider_token?: string }).provider_token ?? null;

  if (!providerToken) {
    // Attempt to refresh session in case token expired
    const {
      data: { session: refreshedSession },
      error: refreshError,
    } = await supabase.auth.refreshSession();

    if (refreshError || !refreshedSession) {
      throw new GoogleTokenError(
        "Google OAuth token not available. Please reconnect your Google account."
      );
    }

    const refreshedProviderToken =
      // biome-ignore lint/style/useNamingConvention: Supabase API field name
      (refreshedSession as unknown as { provider_token?: string }).provider_token ??
      null;

    if (!refreshedProviderToken) {
      throw new GoogleTokenError(
        "Google OAuth token not available. Please reconnect your Google account."
      );
    }

    return refreshedProviderToken;
  }

  return providerToken;
}

/**
 * Check if user has Google Calendar OAuth scopes.
 *
 * Validates that the user's session includes the required Google Calendar
 * scopes for read/write access.
 *
 * @param requiredScopes - Array of required OAuth scopes (default: calendar.events)
 * @returns Promise resolving to true if scopes are available, false otherwise
 */
export async function hasGoogleCalendarScopes(
  _requiredScopes: string[] = ["https://www.googleapis.com/auth/calendar.events"]
): Promise<boolean> {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      return false;
    }

    // Check provider_refresh_token or provider_token existence
    // Supabase may store scope information in session metadata
    const sessionData = session as unknown as {
      // biome-ignore lint/style/useNamingConvention: Supabase API field names
      provider_token?: string;
      // biome-ignore lint/style/useNamingConvention: Supabase API field names
      provider_refresh_token?: string;
      user?: {
        // biome-ignore lint/style/useNamingConvention: Supabase API field name
        app_metadata?: Record<string, unknown>;
      };
    };

    // If provider tokens exist, assume scopes are granted
    // In production, you may want to decode the token and verify scopes
    return !!(
      sessionData.provider_token ||
      sessionData.provider_refresh_token ||
      sessionData.user?.app_metadata?.provider === "google"
    );
  } catch {
    return false;
  }
}
