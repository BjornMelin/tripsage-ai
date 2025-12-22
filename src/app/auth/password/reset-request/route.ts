/**
 * @fileoverview Password reset request route handler.
 */

import "server-only";

import { resetPasswordFormSchema } from "@schemas/auth";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { type RouteParamsContext, withApiGuards } from "@/lib/api/factory";
import { parseJsonBody } from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { getClientIpFromHeaders } from "@/lib/http/ip";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import {
  hashTelemetryFingerprint,
  hashTelemetryIdentifier,
} from "@/lib/telemetry/identifiers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { getRequiredServerOrigin } from "@/lib/url/server-origin";
import { isPlainObject } from "@/lib/utils/type-guards";

interface ResetRequestPayload {
  email?: unknown;
}

const MAX_BODY_BYTES = 16 * 1024;
const RESET_RESPONSE_MESSAGE =
  "If the email exists, you will receive password reset instructions shortly.";

const logger = createServerLogger("auth.password.reset-request");

function getAllowedOrigins(primaryOrigin: string): Set<string> {
  const allowed = new Set<string>();
  const candidates = [
    primaryOrigin,
    process.env.APP_BASE_URL,
    process.env.NEXT_PUBLIC_SITE_URL,
    process.env.NEXT_PUBLIC_APP_URL,
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;
    try {
      allowed.add(new URL(candidate).origin);
    } catch {
      // Ignore malformed env values.
    }
  }

  return allowed;
}

function normalizeBasePath(path: string | undefined): string {
  if (!path) return "";
  const trimmed = path.trim();
  if (!trimmed || trimmed === "/") return "";
  const normalized = trimmed.replace(/^\/+|\/+$/g, "");
  return normalized ? `/${normalized}` : "";
}

/**
 * Handles POST /auth/password/reset-request.
 *
 * Validates the email address and calls Supabase Auth
 * resetPasswordForEmail with a redirect URL pointing back to the app.
 */
const guardedPOST = withApiGuards({
  auth: false,
  degradedMode: "fail_closed",
  rateLimit: "auth:password:reset-request",
  telemetry: "auth.password.reset-request",
})(async (request: NextRequest, { supabase }) => {
  const clientIp = getClientIpFromHeaders(request.headers);
  const ipHash = hashTelemetryIdentifier(clientIp) ?? undefined;
  const userAgent = request.headers.get("user-agent") ?? "";
  const userAgentHash = hashTelemetryFingerprint(userAgent)?.slice(0, 16) ?? undefined;
  const telemetryMeta = { ipHash, userAgentHash };

  const parsedBody = await parseJsonBody(request, { maxBytes: MAX_BODY_BYTES });
  if ("error" in parsedBody) {
    if (parsedBody.error.status === 413) {
      return NextResponse.json(
        { code: "PAYLOAD_TOO_LARGE", message: "Request body exceeds limit" },
        { status: 413 }
      );
    }
    return NextResponse.json(
      { code: "BAD_REQUEST", message: "Malformed JSON" },
      { status: 400 }
    );
  }

  const payload: ResetRequestPayload = isPlainObject(parsedBody.body)
    ? parsedBody.body
    : {};

  const parsed = resetPasswordFormSchema.safeParse({
    email: payload.email,
  });

  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    const message = issue?.message ?? "Email is required";
    return NextResponse.json({ code: "VALIDATION_ERROR", message }, { status: 400 });
  }

  const { email } = parsed.data;

  const requestOrigin = new URL(request.url).origin;
  const configuredOrigin = getRequiredServerOrigin();
  const allowedOrigins = getAllowedOrigins(configuredOrigin);

  if (!allowedOrigins.has(requestOrigin)) {
    const originHash = hashTelemetryFingerprint(requestOrigin)?.slice(0, 16) ?? null;
    emitOperationalAlertOncePerWindow({
      attributes: {
        originHash,
        reason: "invalid_host",
      },
      event: "auth.reset_request.invalid_host",
      severity: "warning",
      windowMs: 60_000,
    });
    logger.warn("password reset request rejected: untrusted origin", {
      ...telemetryMeta,
      originHash,
    });
    return NextResponse.json(
      { code: "INVALID_HOST", message: "Invalid request host" },
      { status: 400 }
    );
  }

  const basePath = normalizeBasePath(
    getServerEnvVarWithFallback("NEXT_PUBLIC_BASE_PATH", "")
  );
  const emailRedirectTo = `${configuredOrigin}${basePath}/auth/reset-password`;

  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: emailRedirectTo,
  });

  if (error) {
    emitOperationalAlertOncePerWindow({
      attributes: {
        errorCode: error.code ?? null,
        reason: "supabase_error",
        status: error.status ?? null,
      },
      event: "auth.reset_request.supabase_error",
      severity: "warning",
      windowMs: 60_000,
    });
    logger.warn("password reset request failed", {
      ...telemetryMeta,
      errorCode: error.code,
      status: error.status,
    });
    return NextResponse.json({ message: RESET_RESPONSE_MESSAGE, ok: true });
  }

  logger.info("password reset request accepted", telemetryMeta);
  return NextResponse.json({ message: RESET_RESPONSE_MESSAGE, ok: true });
});

export const POST = async (req: NextRequest, routeContext: RouteParamsContext) =>
  guardedPOST(req, routeContext);
