/**
 * @fileoverview Supabase authentication callback route handler.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { resolveServerRedirectUrl, safeNextPath } from "@/lib/auth/redirect-server";
import { createServerSupabase } from "@/lib/supabase/server";
import { getOriginFromRequest } from "@/lib/url/server-origin";

/**
 * Handles OAuth callback from Supabase Auth.
 *
 * Exchanges authorization code for session and redirects. Uses safe redirect
 * utilities to prevent open-redirect attacks and correctly handle proxied requests.
 *
 * @param request - Incoming request with auth callback
 * @returns Redirect response to dashboard or specified URL
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const nextParam = searchParams.get("next");

  if (code) {
    const supabase = await createServerSupabase();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      const redirectUrl = resolveServerRedirectUrl(request, nextParam);
      return NextResponse.redirect(redirectUrl);
    }
  }

  // Preserve safe next path for post-login redirect after error resolution
  const origin = getOriginFromRequest(request);
  const safePath = safeNextPath(nextParam);
  const errorUrl = `${origin}/login?error=oauth_failed&next=${encodeURIComponent(safePath)}`;
  return NextResponse.redirect(errorUrl);
}
