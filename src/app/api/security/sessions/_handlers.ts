/**
 * @fileoverview Security session handlers for terminating sessions.
 */

import "server-only";

import { NextResponse } from "next/server";
import { errorResponse, notFoundResponse } from "@/lib/api/route-helpers";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { deleteSingle, getMaybeSingle } from "@/lib/supabase/typed-helpers";
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
      const { data: session, error: fetchError } = await getMaybeSingle(
        adminSupabase,
        "sessions",
        (qb) => qb.eq("id", sessionId).eq("user_id", userId),
        { schema: "auth", select: "id", validate: false }
      );
      if (fetchError) {
        span.setAttribute("security.sessions.terminate.error", true);
        const message =
          fetchError instanceof Error ? fetchError.message : String(fetchError);
        logger.error("session_lookup_failed", {
          error: message,
          sessionIdHash: sessionIdHash ?? undefined,
          userIdHash: userIdHash ?? undefined,
        });
        return errorResponse({
          err: fetchError instanceof Error ? fetchError : new Error(message),
          error: "db_error",
          reason: "Failed to fetch session",
          status: 500,
        });
      }

      if (!session) {
        return notFoundResponse("Session");
      }

      const deleteResult = await deleteSingle(
        adminSupabase,
        "sessions",
        (qb) => qb.eq("id", sessionId).eq("user_id", userId),
        { schema: "auth" }
      );

      if (deleteResult.error) {
        const message =
          deleteResult.error instanceof Error
            ? deleteResult.error.message
            : String(deleteResult.error);
        span.setAttribute("security.sessions.terminate.error", true);
        logger.error("session_delete_failed", {
          error: message,
          sessionIdHash: sessionIdHash ?? undefined,
          userIdHash: userIdHash ?? undefined,
        });
        return errorResponse({
          err:
            deleteResult.error instanceof Error
              ? deleteResult.error
              : new Error(message),
          error: "db_error",
          reason: "Failed to terminate session",
          status: 500,
        });
      }

      return new NextResponse(null, { status: 204 });
    }
  );
}
