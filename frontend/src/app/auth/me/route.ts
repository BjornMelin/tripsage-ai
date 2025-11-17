/**
 * @fileoverview Auth session introspection route.
 *
 * Returns the current authenticated user in the frontend AuthUser shape using
 * Supabase SSR cookies as the session source of truth.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getOptionalUser, mapSupabaseUserToAuthUser } from "@/lib/auth/server";
import type { AuthUser } from "@/lib/schemas/stores";

interface MeResponse {
  user: AuthUser | null;
}

/**
 * Handles GET /auth/me.
 *
 * When authenticated, returns `{ user }` with the mapped AuthUser shape.
 * When unauthenticated, returns `{ user: null }` with HTTP 401.
 */
export async function GET(_req: NextRequest): Promise<NextResponse<MeResponse>> {
  const { user } = await getOptionalUser();

  if (!user) {
    return NextResponse.json({ user: null }, { status: 401 });
  }

  const mappedUser = mapSupabaseUserToAuthUser(user);
  return NextResponse.json({ user: mappedUser }, { status: 200 });
}
