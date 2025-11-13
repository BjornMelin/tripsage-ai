/**
 * @fileoverview File attachment webhook handler for upload status changes.
 */

import "server-only";
import { SpanStatusCode } from "@opentelemetry/api";
import { createClient } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";
import { getServerEnvVar } from "@/lib/env/server";
import { tryReserveKey } from "@/lib/idempotency/redis";
import type { Database } from "@/lib/supabase/database.types";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { buildEventKey, parseAndVerify } from "@/lib/webhooks/payload";

type FileAttachmentRow = Database["public"]["Tables"]["file_attachments"]["Row"];

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * Creates an admin Supabase client with service role credentials.
 *
 * @return Admin Supabase client instance.
 * @throws When SUPABASE_SERVICE_ROLE_KEY is not configured.
 */
function createAdminSupabase() {
  const url = getServerEnvVar("NEXT_PUBLIC_SUPABASE_URL");
  const serviceKey = getServerEnvVar("SUPABASE_SERVICE_ROLE_KEY");
  if (!serviceKey) {
    throw new Error(
      "SUPABASE_SERVICE_ROLE_KEY is required for file webhook processing"
    );
  }
  return createClient<Database>(url, serviceKey);
}

/**
 * Handles file attachment database change webhooks.
 *
 * @param req - The incoming webhook request.
 * @return Response indicating success or error.
 */
export async function POST(req: NextRequest) {
  return await withTelemetrySpan(
    "webhook.files",
    { attributes: { route: "/api/hooks/files" } },
    async (span) => {
      const { ok, payload } = await parseAndVerify(req);
      if (!ok || !payload)
        return NextResponse.json(
          { error: "invalid signature or payload" },
          { status: 401 }
        );
      span.setAttribute("table", payload.table);
      span.setAttribute("op", payload.type);
      if (payload.table !== "file_attachments") {
        return NextResponse.json({ ok: true, skipped: true });
      }

      const eventKey = buildEventKey(payload);
      span.setAttribute("event.key", eventKey);
      const unique = await tryReserveKey(eventKey, 300);
      if (!unique) return NextResponse.json({ duplicate: true, ok: true });

      const supabase = createAdminSupabase();
      const record = payload.record as Partial<FileAttachmentRow> | null;
      const attachmentId = record?.id;
      const uploadStatus = record?.upload_status;
      if (payload.type === "INSERT" && attachmentId && uploadStatus === "uploading") {
        const { error } = await supabase
          .from("file_attachments")
          .select("id")
          .eq("id", attachmentId)
          .limit(1)
          .single();
        if (error) {
          span.recordException(error);
          span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
          return NextResponse.json({ error: "supabase error" }, { status: 500 });
        }
      }
      return NextResponse.json({ ok: true });
    }
  );
}
