/**
 * @fileoverview CSP violation report collection endpoint.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody } from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";

const MAX_REPORT_BYTES = 16 * 1024;
const MAX_REPORT_FIELD_CHARS = 256;

const cspReportSchema = z.record(z.string(), z.unknown());

const cspReportEnvelopeSchema = z
  .looseObject({
    "csp-report": cspReportSchema.optional(),
  })
  .or(cspReportSchema);

const logger = createServerLogger("security.csp-report");

function getReportObject(
  value: z.infer<typeof cspReportEnvelopeSchema>
): Record<string, unknown> {
  if (
    typeof value === "object" &&
    value !== null &&
    "csp-report" in value &&
    typeof value["csp-report"] === "object" &&
    value["csp-report"] !== null
  ) {
    return value["csp-report"] as Record<string, unknown>;
  }
  return value;
}

function getReportString(report: Record<string, unknown>, key: string): string | null {
  const value = report[key];
  return typeof value === "string" ? limitReportField(value.trim()) : null;
}

function limitReportField(value: string): string {
  return value.length > MAX_REPORT_FIELD_CHARS
    ? `${value.slice(0, MAX_REPORT_FIELD_CHARS)}...`
    : value;
}

function sanitizeReportUri(value: string | null): string | null {
  const text = value?.trim();
  if (!text) return null;

  const lowered = text.toLowerCase();
  if (["inline", "eval", "wasm-eval"].includes(lowered)) return lowered;
  if (lowered.startsWith("data:")) return "data:";
  if (lowered.startsWith("blob:")) return "blob:";

  try {
    const url = new URL(text);
    return limitReportField(url.origin);
  } catch {
    return limitReportField(text.split(/[?#]/, 1)[0] ?? text);
  }
}

function sanitizeDisposition(value: string | null): "enforce" | "report" | null {
  return value === "enforce" || value === "report" ? value : null;
}

function sanitizeDirective(value: string | null): string | null {
  if (!value) return null;
  const directive = value.trim().split(/\s+/, 1)[0] ?? "";
  return /^[a-z0-9-]+$/i.test(directive) ? limitReportField(directive) : null;
}

/**
 * POST handler for CSP violation reports emitted by enforced/report-only policies.
 *
 * @param req - Next.js request containing a CSP report payload.
 * @returns Empty response when accepted, or a standardized error response for malformed input.
 */
export const POST = withApiGuards({
  rateLimit: "security:csp-report",
  telemetry: "security.csp-report",
})(async (req: NextRequest) => {
  const parsedBody = await parseJsonBody(req, { maxBytes: MAX_REPORT_BYTES });
  if (!parsedBody.ok) {
    return parsedBody.error.status === 413
      ? parsedBody.error
      : errorResponse({
          error: "invalid_report",
          reason: "Malformed CSP report",
          status: 400,
        });
  }

  const parsedReport = cspReportEnvelopeSchema.safeParse(parsedBody.data);
  if (!parsedReport.success) {
    return errorResponse({
      err: parsedReport.error,
      error: "invalid_report",
      reason: "Invalid CSP report",
      status: 400,
    });
  }

  const report = getReportObject(parsedReport.data);
  logger.warn("csp_violation_report", {
    blockedUri: sanitizeReportUri(
      getReportString(report, "blocked-uri") ?? getReportString(report, "blockedURL")
    ),
    disposition: sanitizeDisposition(getReportString(report, "disposition")),
    documentUri: sanitizeReportUri(
      getReportString(report, "document-uri") ?? getReportString(report, "documentURL")
    ),
    effectiveDirective: sanitizeDirective(
      getReportString(report, "effective-directive") ??
        getReportString(report, "effectiveDirective") ??
        getReportString(report, "violated-directive") ??
        getReportString(report, "violatedDirective") ??
        getReportString(report, "directive")
    ),
  });

  return new NextResponse(null, { status: 204 });
});
