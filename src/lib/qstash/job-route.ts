/**
 * @fileoverview Shared QStash job route helper (verify + idempotency + JSON validation).
 */

import "server-only";

import { NextResponse } from "next/server";
import type { z } from "zod";
import { errorResponse } from "@/lib/api/route-helpers";
import type {
  QstashIdempotencyResult,
  QstashRequestMeta,
  VerifyQstashRequestResult,
} from "@/lib/qstash/receiver";
import {
  enforceQstashMessageIdempotency,
  getQstashReceiver,
  QstashIdempotencyCommitError,
  qstashNonRetryableErrorResponse,
  verifyQstashRequest,
} from "@/lib/qstash/receiver";

export interface QstashJobSpan {
  addEvent?(
    name: string,
    attributesOrStartTime?: unknown,
    startTime?: unknown
  ): unknown;
  recordException(error: Error): void;
  setAttribute(key: string, value: boolean | number | string): void;
}

export interface RunQstashJobOptions<T> {
  req: Request;
  span: QstashJobSpan;
  schema: z.ZodType<T>;
  verifyMaxBytes?: number;
  lockTtlSeconds?: number;
  processedTtlSeconds?: number;
  internalErrorReason: string;
  onVerifyFailure?: (
    result: Extract<VerifyQstashRequestResult, { ok: false }>,
    req: Request,
    span: QstashJobSpan
  ) => void;
  onPayloadValidated?: (
    payload: T,
    meta: QstashRequestMeta,
    span: QstashJobSpan
  ) => void;
  mapNonRetryableError?: (error: unknown) => { error: string; reason: string } | null;
  handle: (
    payload: T,
    meta: QstashRequestMeta,
    span: QstashJobSpan
  ) => Promise<unknown>;
}

function isProcessGuard(
  guard: QstashIdempotencyResult
): guard is Extract<QstashIdempotencyResult, { ok: true; outcome: "process" }> {
  return guard.ok && guard.outcome === "process";
}

export async function runQstashJob<T>(
  options: RunQstashJobOptions<T>
): Promise<Response> {
  const { req, span } = options;
  let guard: QstashIdempotencyResult | null = null;

  try {
    let receiver: ReturnType<typeof getQstashReceiver>;
    try {
      receiver = getQstashReceiver();
    } catch (error) {
      span.recordException(error as Error);
      return errorResponse({
        err: error,
        error: "configuration_error",
        reason: "QStash signing keys are misconfigured",
        status: 500,
      });
    }

    const verified = await verifyQstashRequest(req, receiver, {
      maxBytes: options.verifyMaxBytes,
    });
    if (!verified.ok) {
      options.onVerifyFailure?.(verified, req, span);
      return verified.response;
    }

    guard = await enforceQstashMessageIdempotency(req, {
      lockTtlSeconds: options.lockTtlSeconds,
      processedTtlSeconds: options.processedTtlSeconds,
    });
    if (!guard.ok) return guard.response;

    span.setAttribute("qstash.message_id", guard.meta.messageId);
    span.setAttribute("qstash.attempt", guard.meta.retried + 1);

    if (guard.outcome === "duplicate") {
      span.setAttribute("qstash.duplicate", true);
      return NextResponse.json({ duplicate: true, ok: true }, { status: 200 });
    }

    let json: unknown;
    try {
      json = JSON.parse(verified.body) as unknown;
    } catch (error) {
      await guard.release().catch(() => undefined);
      return qstashNonRetryableErrorResponse({
        err: error,
        error: "invalid_request",
        reason: "Malformed JSON in request body",
      });
    }

    const parsed = options.schema.safeParse(json);
    if (!parsed.success) {
      await guard.release().catch(() => undefined);
      return qstashNonRetryableErrorResponse({
        err: parsed.error,
        error: "invalid_request",
        issues: parsed.error.issues,
        reason: "Request validation failed",
      });
    }

    options.onPayloadValidated?.(parsed.data, guard.meta, span);

    const result = await options.handle(parsed.data, guard.meta, span);
    await guard.commitProcessed();
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    span.recordException(error as Error);
    const processGuard = guard && isProcessGuard(guard) ? guard : null;
    if (processGuard && !(error instanceof QstashIdempotencyCommitError)) {
      await processGuard.release().catch(() => undefined);
    }

    const mapped = options.mapNonRetryableError?.(error);
    if (mapped) {
      return qstashNonRetryableErrorResponse({
        err: error,
        error: mapped.error,
        reason: mapped.reason,
      });
    }

    return errorResponse({
      err: error,
      error: "internal",
      reason: options.internalErrorReason,
      status: 500,
    });
  }
}
