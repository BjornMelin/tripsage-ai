/**
 * @fileoverview Server-side auth helpers for Next.js App Router.
 *
 * Provides `requireUser` and `getOptionalUser` helpers that wrap the Supabase
 * SSR client and unified getCurrentUser helper. These are intended for use in
 * Server Components, Route Handlers, and Server Actions.
 */

import "server-only";

import type { AuthUser } from "@schemas/stores";
import type { User } from "@supabase/supabase-js";
import { redirect } from "next/navigation";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerSupabase, getCurrentUser } from "@/lib/supabase/server";

export interface AuthContext {
  supabase: TypedServerSupabase;
  user: User;
}

export interface OptionalAuthContext {
  supabase: TypedServerSupabase;
  user: User | null;
}

/**
 * Maps a Supabase `User` into the frontend `AuthUser` shape.
 *
 * Uses user_metadata fields when present and falls back to email-derived
 * display names where appropriate.
 *
 * @param user - Supabase Auth user
 * @returns Mapped AuthUser object
 */
export function mapSupabaseUserToAuthUser(user: User): AuthUser {
  const metadata = (user.user_metadata ?? {}) as Record<string, unknown>;
  const fullName =
    (metadata.full_name as string | undefined) ??
    (metadata.display_name as string | undefined);

  const firstName = (metadata.first_name as string | undefined) ?? undefined;
  const lastName = (metadata.last_name as string | undefined) ?? undefined;

  const displayName =
    fullName ??
    (metadata.display_name as string | undefined) ??
    firstName ??
    (user.email ? user.email.split("@")[0] : undefined);

  return {
    avatarUrl: (metadata.avatar_url as string | undefined) ?? undefined,
    bio: (metadata.bio as string | undefined) ?? undefined,
    createdAt: user.created_at,
    displayName,
    email: user.email ?? "",
    firstName,
    id: user.id,
    isEmailVerified: Boolean(user.email_confirmed_at),
    lastName,
    location: (metadata.location as string | undefined) ?? undefined,
    preferences: undefined,
    security: undefined,
    updatedAt: user.updated_at ?? user.created_at,
    website: (metadata.website as string | undefined) ?? undefined,
  };
}

/**
 * Returns the current user if present, or null when unauthenticated.
 *
 * @returns Supabase client and optional user
 */
export async function getOptionalUser(): Promise<OptionalAuthContext> {
  const supabase = await createServerSupabase();
  const { user } = await getCurrentUser(supabase);
  return { supabase, user };
}

/**
 * Returns the current authenticated user or redirects to /login when missing.
 *
 * @param options Optional redirect configuration
 * @returns Supabase client and authenticated user
 */
export async function requireUser(
  options: { redirectTo?: string } = {}
): Promise<AuthContext> {
  const { supabase, user } = await getOptionalUser();
  if (!user) {
    const target = options.redirectTo ?? "/dashboard";
    const loginUrl = `/login?next=${encodeURIComponent(target)}`;
    redirect(loginUrl);
  }
  return { supabase, user };
}
