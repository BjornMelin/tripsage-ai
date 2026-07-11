/**
 * @fileoverview Authenticated account deletion route. Deletes the current user via Supabase admin API using the service-role key.
 */

import "server-only";

import { NextResponse } from "next/server";
import { authRouteErrorResponse } from "@/lib/auth/route-error-response";
import { getOptionalUser } from "@/lib/auth/server";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("auth.delete");

/**
 * Handles DELETE /auth/delete requests from client-side consumers.
 *
 * Deletes the current user via Supabase admin API using the service-role key.
 */
export async function DELETE(): Promise<NextResponse> {
  try {
    const { supabase, user } = await getOptionalUser();
    if (!user) {
      return authRouteErrorResponse({
        code: "UNAUTHORIZED",
        reason: "Authentication required",
        status: 401,
      });
    }
    const admin = createAdminSupabase();

    const { error } = await admin.auth.admin.deleteUser(user.id);
    if (error) {
      return authRouteErrorResponse({
        code: "DELETE_FAILED",
        reason: error.message,
        status: 400,
      });
    }

    try {
      const { error: signOutError } = await supabase.auth.signOut({ scope: "local" });
      if (signOutError) {
        logger.warn("auth.delete.local_sign_out_failed", {
          message: signOutError.message,
        });
      }
    } catch (error) {
      logger.warn("auth.delete.local_sign_out_failed", {
        message: error instanceof Error ? error.message : "unknown_error",
      });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to delete account.";
    return authRouteErrorResponse({
      code: "DELETE_FAILED",
      reason: message,
      status: 500,
    });
  }
}
