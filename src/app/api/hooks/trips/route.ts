/**
 * @fileoverview Trip collaborator webhook handler with async notification queuing.
 *
 * Uses the shared webhook handler abstraction to reduce boilerplate.
 * Enqueues notifications via QStash with ADR-0048 retry policy.
 */

import "server-only";

import { after } from "next/server";
import { sendCollaboratorNotifications } from "@/lib/notifications/collaborators";
import { tryEnqueueJob } from "@/lib/qstash/client";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { createWebhookHandler } from "@/lib/webhooks/handler";

type TripCollaboratorRow = Database["public"]["Tables"]["trip_collaborators"]["Row"];

const logger = createServerLogger("webhook.trips");

/**
 * Handles trip collaborator database change webhooks with async notification processing.
 *
 * Features (via handler abstraction):
 * - Rate limiting (100 req/min per IP)
 * - Body size validation (64KB max)
 * - HMAC signature verification
 * - Table filtering (trip_collaborators only)
 * - Idempotency via Redis
 */
export const POST = createWebhookHandler({
  enableIdempotency: true,

  async handle(payload, eventKey, span) {
    // Validate trip exists (optional integrity check)
    const collaboratorRecord = (payload.record ??
      payload.oldRecord) as Partial<TripCollaboratorRow> | null;
    const tripIdValue = collaboratorRecord?.trip_id;
    const tripId = typeof tripIdValue === "number" ? tripIdValue : undefined;

    if (tripId) {
      const supabase = createAdminSupabase();
      const { error } = await supabase
        .from("trips")
        .select("id")
        .eq("id", tripId)
        .limit(1);

      if (error) {
        span.recordException(error);
        throw error; // Will be caught by handler and return 500
      }
    }

    // Primary path: enqueue to QStash worker for durable retries
    const result = await tryEnqueueJob(
      "notify-collaborators",
      { eventKey, payload },
      "/api/jobs/notify-collaborators"
    );

    if (result.success) {
      span.setAttribute("qstash.message_id", result.messageId);
      return { enqueued: true };
    }

    // Fallback: fire-and-forget via after() if QStash unavailable
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

    return { enqueued: false, fallback: true };
  },
  idempotencyTTL: 300,
  name: "trips",
  tableFilter: "trip_collaborators",
});
