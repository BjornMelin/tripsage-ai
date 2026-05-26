/**
 * @fileoverview Authenticated account deletion route. Deletes the current user via Supabase admin API using the service-role key.
 */

import "server-only";

import { NextResponse } from "next/server";
import { authRouteErrorResponse } from "@/lib/auth/route-error-response";
import { requireUser } from "@/lib/auth/server";
import { createAdminSupabase } from "@/lib/supabase/admin";

/**
 * Handles DELETE /auth/delete requests from client-side consumers.
 *
 * Deletes the current user via Supabase admin API using the service-role key.
 */
export async function DELETE(): Promise<NextResponse> {
  try {
    const { user } = await requireUser({ redirectTo: "/login" });
    const admin = createAdminSupabase();

    const { error } = await admin.auth.admin.deleteUser(user.id);
    if (error) {
      return authRouteErrorResponse({
        code: "DELETE_FAILED",
        reason: error.message,
        status: 400,
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
