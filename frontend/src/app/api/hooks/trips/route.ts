/**
 * @fileoverview Trip collaborator webhook handler with async notification queuing.
 */

import "server-only";
import { createClient } from "@supabase/supabase-js";
import { Client as QStash } from "@upstash/qstash";
import { after, type NextRequest, NextResponse } from "next/server";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { tryReserveKey } from "@/lib/idempotency/redis";
import { sendCollaboratorNotifications } from "@/lib/notifications/collaborators";
import type { Database } from "@/lib/supabase/database.types";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { buildEventKey, parseAndVerify } from "@/lib/webhooks/payload";

type TripCollaboratorRow = Database["public"]["Tables"]["trip_collaborators"]["Row"];

/**
 * Creates an admin Supabase client with service role credentials.
 *
 * @return Admin Supabase client instance.
 */
function createAdminSupabase() {
  const url = getServerEnvVar("NEXT_PUBLIC_SUPABASE_URL");
  const serviceKey = getServerEnvVar("SUPABASE_SERVICE_ROLE_KEY") as string;
  return createClient<Database>(url, serviceKey);
}

/**
 * Handles trip collaborator database change webhooks with async notification processing.
 *
 * @param req - The incoming webhook request.
 * @return Response indicating success or error.
 */
export async function POST(req: NextRequest) {
  const logger = createServerLogger("webhook.trips");
  return await withTelemetrySpan(
    "webhook.trips",
    { attributes: { route: "/api/hooks/trips" } },
    async (span) => {
      const { ok, payload } = await parseAndVerify(req);
      if (!ok || !payload)
        return NextResponse.json(
          { error: "invalid signature or payload" },
          { status: 401 }
        );
      span.setAttribute("table", payload.table);
      span.setAttribute("op", payload.type);
      if (payload.table !== "trip_collaborators") {
        return NextResponse.json({ ok: true, skipped: true });
      }

      const eventKey = buildEventKey(payload);
      span.setAttribute("event.key", eventKey);
      const unique = await tryReserveKey(eventKey, 300);
      if (!unique) {
        span.setAttribute("event.duplicate", true);
        return NextResponse.json({ duplicate: true, ok: true });
      }

      const supabase = createAdminSupabase();
      const collaboratorRecord = (payload.record ??
        payload.oldRecord) as Partial<TripCollaboratorRow> | null;
      const tripIdValue = collaboratorRecord?.trip_id;
      const tripId = typeof tripIdValue === "number" ? tripIdValue : undefined;
      if (tripId) {
        const { error } = await supabase
          .from("trips")
          .select("id")
          .eq("id", tripId)
          .limit(1);
        if (error) {
          span.recordException(error);
          return NextResponse.json({ error: "supabase query failed" }, { status: 500 });
        }
      }

      // Primary path: enqueue to QStash worker for durable retries
      const qstashToken = getServerEnvVarWithFallback("QSTASH_TOKEN", "");
      if (qstashToken) {
        const q = new QStash({ token: qstashToken });
        const workerUrl = `${req.nextUrl.origin}/api/jobs/notify-collaborators`;
        await q.publishJSON({ body: { eventKey, payload }, url: workerUrl });
        return NextResponse.json({ enqueued: true, ok: true });
      }

      // Fallback: fire-and-forget via after() if QStash not configured
      after(async () => {
        try {
          await withTelemetrySpan(
            "webhook.trips.fallback",
            {
              attributes: {
                "event.key": eventKey,
                fallback: true,
                route: "/api/hooks/trips",
              },
            },
            async () => {
              await sendCollaboratorNotifications(payload, eventKey);
            }
          );
        } catch (err) {
          // Swallow to avoid rethrowing inside after(); telemetry span captures the error
          logger.error("fallback_failed", {
            error: err instanceof Error ? err.message : "unknown_error",
            eventKey,
          });
        }
      });
      return NextResponse.json({ enqueued: false, fallback: true, ok: true });
    }
  );
}
