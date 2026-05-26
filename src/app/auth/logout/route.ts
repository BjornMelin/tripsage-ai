/**
 * @fileoverview Supabase logout route handler.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { authRouteErrorResponse } from "@/lib/auth/route-error-response";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("auth.logout");

/**
 * Handles POST /auth/logout requests from client-side consumers.
 *
 * Clears the Supabase session via supabase.auth.signOut() and returns a JSON
 * response. Clients are responsible for updating their own view state.
 */
export async function POST(_request: NextRequest): Promise<NextResponse> {
  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signOut();

  if (error) {
    logger.error("auth.logout.sign_out_failed", { message: error.message });
    return authRouteErrorResponse({
      error: "logout_failed",
      reason: "Logout failed",
      status: 500,
    });
  }

  return NextResponse.json({ success: true });
}

/**
 * Handles GET /auth/logout for hyperlink-based logout.
 *
 * Signs the user out and redirects them to the login page.
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  const supabase = await createServerSupabase();
  await supabase.auth.signOut();

  const url = new URL("/login", request.url);
  return NextResponse.redirect(url);
}
