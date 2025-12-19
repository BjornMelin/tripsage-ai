/**
 * @fileoverview Security session handlers for terminating sessions.
 */

import "server-only";

import { NextResponse } from "next/server";
import { errorResponse, notFoundResponse } from "@/lib/api/route-helpers";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { hashTelemetryIdentifier } from "@/lib/telemetry/identifiers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const logger = createServerLogger("api.security.sessions");

/**
 * Terminates a specific session owned by the user.
 *
 * @param params - The parameters for the terminate session handler.
 * @returns The terminate session response.
 */
export async function terminateSessionHandler(params: {
  adminSupabase: TypedAdminSupabase;
  sessionId: string;
  userId: string;
}): Promise<NextResponse> {
  const { adminSupabase, sessionId, userId } = params;
  const sessionIdHash = hashTelemetryIdentifier(sessionId);
  const userIdHash = hashTelemetryIdentifier(userId);

  return await withTelemetrySpan(
    "security.sessions.terminate",
    {
      attributes: {
        ...(sessionIdHash ? { "session.id_hash": sessionIdHash } : {}),
        ...(userIdHash ? { "user.id_hash": userIdHash } : {}),
      },
    },
    async (span) => {
      const sessionQuery = adminSupabase
        .schema("auth")
        .from("sessions")
        .select("id")
        .eq("id", sessionId)
        .eq("user_id", userId)
        .maybeSingle();

      const { data: session, error: fetchError } = await sessionQuery;
      if (fetchError) {
        span.setAttribute("security.sessions.terminate.error", true);
        logger.error("session_lookup_failed", {
          error: fetchError.message,
          sessionIdHash: sessionIdHash ?? undefined,
          userIdHash: userIdHash ?? undefined,
        });
        return errorResponse({
          err: fetchError,
          error: "db_error",
          reason: "Failed to fetch session",
          status: 500,
        });
      }

      if (!session) {
        return notFoundResponse("Session");
      }

      const deleteResult = await adminSupabase
        .schema("auth")
        .from("sessions")
        .delete()
        .eq("id", sessionId)
        .eq("user_id", userId);

      if (deleteResult.error) {
        span.setAttribute("security.sessions.terminate.error", true);
        logger.error("session_delete_failed", {
          error: deleteResult.error.message,
          sessionIdHash: sessionIdHash ?? undefined,
          userIdHash: userIdHash ?? undefined,
        });
        return errorResponse({
          err: deleteResult.error,
          error: "db_error",
          reason: "Failed to terminate session",
          status: 500,
        });
      }

      return new NextResponse(null, { status: 204 });
    }
  );
}
