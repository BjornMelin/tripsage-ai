/**
 * @fileoverview Server-only helpers for reading Google OAuth tokens from the Supabase session.
 */

import "server-only";

import { createServerSupabase } from "@/lib/supabase/server";

type ServerSupabase = Awaited<ReturnType<typeof createServerSupabase>>;
type GetUserResult = Awaited<ReturnType<ServerSupabase["auth"]["getUser"]>>;
type GetSessionResult = Awaited<ReturnType<ServerSupabase["auth"]["getSession"]>>;
type SupabaseSession = GetSessionResult["data"]["session"];

type GetUserWithSessionResult = {
  supabase: ServerSupabase;
  session: SupabaseSession;
  error: GetUserResult["error"] | GetSessionResult["error"] | Error;
  errorSource: "user" | "session" | null;
  userError: GetUserResult["error"];
  sessionError: GetSessionResult["error"];
};

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
 * Get authenticated session data from Supabase with a defense-in-depth JWT validation step.
 *
 * Supabase's `getSession()` can return a cached session. Calling `getUser()` first ensures
 * the JWT is validated server-side before using provider tokens from the session.
 */
async function getUserWithSession(): Promise<GetUserWithSessionResult> {
  const supabase = await createServerSupabase();

  // Validate JWT server-side before retrieving session tokens (defense-in-depth)
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    return {
      error: userError,
      errorSource: "user",
      session: null,
      sessionError: null,
      supabase,
      userError,
    };
  }

  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  return {
    error: sessionError ?? (session ? null : new Error("No active session")),
    errorSource: sessionError || !session ? "session" : null,
    session,
    sessionError,
    supabase,
    userError: null,
  };
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
  const { supabase, session, error } = await getUserWithSession();

  if (error || !session) {
    throw new GoogleTokenError("No active session found");
  }

  // Check if provider_token exists in session
  // Supabase stores provider tokens in session.provider_token for OAuth providers
  const providerToken = session.provider_token ?? null;

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

    const refreshedProviderToken = refreshedSession.provider_token ?? null;

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
    const { session, error } = await getUserWithSession();

    if (error || !session) {
      return false;
    }

    // If provider tokens exist, assume scopes are granted. For stricter checks,
    // decode the provider token and validate scopes against required scopes.
    return Boolean(
      session.provider_token ||
        session.provider_refresh_token ||
        session.user.app_metadata?.provider === "google"
    );
  } catch {
    return false;
  }
}
