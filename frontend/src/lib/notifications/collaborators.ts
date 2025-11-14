/**
 * @fileoverview Trip collaborator notification utilities with email and webhook support.
 */

import "server-only";

import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import type { Database } from "@/lib/supabase/database.types";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import type { WebhookPayload } from "@/lib/webhooks/payload";

type TripCollaboratorRow = Database["public"]["Tables"]["trip_collaborators"]["Row"];

/**
 * Creates an admin Supabase client with service role credentials.
 *
 * @return Admin Supabase client instance.
 * @throws When Supabase credentials are not configured.
 */
function createAdminSupabase() {
  const url = getServerEnvVarWithFallback("NEXT_PUBLIC_SUPABASE_URL", "");
  const serviceKey = getServerEnvVarWithFallback("SUPABASE_SERVICE_ROLE_KEY", "");
  if (!url || !serviceKey) {
    throw new Error("Supabase admin credentials are required for notifications");
  }
  return createClient<Database>(url, serviceKey);
}

/**
 * Looks up a user's email address by their user ID.
 *
 * @param userId - The user's unique identifier.
 * @return User's email address or null if not found.
 */
async function lookupUserEmail(userId: string): Promise<string | null> {
  const supabase = createAdminSupabase();
  const { data, error } = await supabase.auth.admin.getUserById(userId);
  if (error || !data?.user?.email) return null;
  return data.user.email;
}

/**
 * Sends notifications for trip collaborator changes via email and webhooks.
 *
 * @param event - The webhook payload containing the collaborator change.
 * @param eventKey - Unique identifier for the event to prevent duplicates.
 * @return Object indicating which notification methods succeeded.
 */
export async function sendCollaboratorNotifications(
  event: WebhookPayload,
  eventKey: string
): Promise<{ emailed?: boolean; webhookPosted?: boolean }> {
  return await withTelemetrySpan(
    "notifications.collaborators",
    { attributes: { eventKey, table: event.table, type: event.type } },
    async (span) => {
      if (event.table !== "trip_collaborators") {
        return {};
      }

      const rec = extractCollaboratorRecord(event);

      const userId = rec?.userId;
      let emailed = false;
      let webhookPosted = false;

      const resendKey = getServerEnvVarWithFallback("RESEND_API_KEY", "");
      const fromEmail = getServerEnvVarWithFallback(
        "RESEND_FROM_EMAIL",
        "noreply@tripsage.com"
      );
      const fromName = getServerEnvVarWithFallback("RESEND_FROM_NAME", "TripSage");
      const downstreamUrl = getServerEnvVarWithFallback(
        "COLLAB_WEBHOOK_URL",
        undefined as unknown as string | undefined
      );

      // Email via Resend (if configured and user email is resolvable)
      if (resendKey && userId) {
        const email = await lookupUserEmail(userId);
        if (email) {
          const resend = new Resend(resendKey);
          const subject = buildSubject(event);
          const text = buildBody(event, eventKey);
          try {
            await resend.emails.send({
              from: `${fromName} <${fromEmail}>`,
              headers: { "X-Idempotency-Key": eventKey },
              subject,
              text,
              to: [email],
            });
            emailed = true;
          } catch (err) {
            span.recordException(err as Error);
          }
        }
      }

      // Optional downstream webhook
      if (downstreamUrl) {
        try {
          const controller = new AbortController();
          const id = setTimeout(() => controller.abort(), 1500);
          const resp = await fetch(downstreamUrl, {
            body: JSON.stringify({ event, eventKey }),
            headers: {
              "content-type": "application/json",
              "x-event-key": eventKey,
            },
            method: "POST",
            signal: controller.signal,
          });
          clearTimeout(id);
          if (resp.ok) webhookPosted = true;
        } catch (err) {
          span.recordException(err as Error);
        }
      }

      return { emailed, webhookPosted };
    }
  );
}

/**
 * Builds email subject line for collaborator notifications.
 *
 * @param event - The webhook payload.
 * @return Appropriate subject line for the event type.
 */
function buildSubject(event: WebhookPayload): string {
  switch (event.type) {
    case "INSERT":
      return "You were added as a trip collaborator";
    case "UPDATE":
      return "Your trip collaborator role changed";
    case "DELETE":
      return "You were removed as a trip collaborator";
    default:
      return "Trip collaboration update";
  }
}

/**
 * Builds email body content for collaborator notifications.
 *
 * @param event - The webhook payload.
 * @param eventKey - Unique event identifier.
 * @return Email body content.
 */
function buildBody(event: WebhookPayload, eventKey: string): string {
  const rec = extractCollaboratorRecord(event);
  const tripRef = rec?.tripId ? `Trip #${rec.tripId}` : "a trip";
  switch (event.type) {
    case "INSERT":
      return `${tripRef}: You have been added as a collaborator.\nEvent: ${eventKey}`;
    case "UPDATE":
      return `${tripRef}: Your collaborator permissions were updated to ${rec?.permissionLevel ?? "updated"}.\nEvent: ${eventKey}`;
    case "DELETE":
      return `${tripRef}: You have been removed as a collaborator.\nEvent: ${eventKey}`;
    default:
      return `${tripRef}: Collaboration updated.\nEvent: ${eventKey}`;
  }
}
/**
 * Extracted collaborator record fields from webhook payload.
 */
type CollaboratorRecord = {
  permissionLevel?: string;
  tripId?: number;
  userId?: string;
};

/**
 * Extracts collaborator record fields from webhook payload.
 *
 * @param event - The webhook payload.
 * @return Extracted collaborator record or null if no relevant fields.
 */
function extractCollaboratorRecord(event: WebhookPayload): CollaboratorRecord | null {
  const source = (event.record ??
    event.oldRecord) as Partial<TripCollaboratorRow> | null;
  if (!source) return null;
  const tripIdValue = source.trip_id;
  const userIdValue = source.user_id;
  const permissionLevelValue = source.permission_level;
  const tripId = typeof tripIdValue === "number" ? tripIdValue : undefined;
  const userId = typeof userIdValue === "string" ? userIdValue : undefined;
  const permissionLevel =
    typeof permissionLevelValue === "string" ? permissionLevelValue : undefined;
  if (!tripId && !userId && !permissionLevel) {
    return null;
  }
  return {
    permissionLevel,
    tripId,
    userId,
  };
}
