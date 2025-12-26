/**
 * @fileoverview Shared QStash client with enforced retry policy per ADR-0048.
 */

import "server-only";

import { Client } from "@upstash/qstash";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";
import { QSTASH_RETRY_CONFIG } from "./config";

// ===== TYPES =====

/**
 * QStash client interface for dependency injection.
 * Matches the subset of Client methods we use.
 */
// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
export type QStashClientLike = {
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash method name
  publishJSON: (opts: {
    url: string;
    body: unknown;
    headers?: Record<string, string>;
    retries?: number;
    delay?: number;
    deduplicationId?: string;
    callback?: string;
  }) => Promise<{ messageId: string; url?: string; scheduled?: boolean }>;
};

// ===== TEST INJECTION =====

// Test injection point (follows factory.ts pattern)
let testClientFactory: (() => QStashClientLike) | null = null;

/**
 * Override QStash client factory for tests.
 * Pass null to reset to production behavior.
 *
 * @example
 * ```ts
 * import { setQStashClientFactoryForTests } from "@/lib/qstash/client";
 * import { createQStashMock } from "@/test/upstash/qstash-mock";
 *
 * const qstash = createQStashMock();
 * setQStashClientFactoryForTests(() => new qstash.Client({ token: "test" }));
 *
 * // After tests
 * setQStashClientFactoryForTests(null);
 * ```
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export function setQStashClientFactoryForTests(
  factory: (() => QStashClientLike) | null
): void {
  testClientFactory = factory;
}

// ===== CLIENT SINGLETON =====

let qstashClient: QStashClientLike | null = null;

/**
 * Get or create the QStash client singleton.
 * Uses test factory if set, otherwise creates production client.
 *
 * @returns QStash client or null if QSTASH_TOKEN is not configured
 */
export function getQstashClient(): QStashClientLike | null {
  if (testClientFactory) return testClientFactory();
  if (qstashClient) return qstashClient;

  const token = getServerEnvVarWithFallback("QSTASH_TOKEN", "");
  if (!token) return null;

  qstashClient = new Client({ token });
  return qstashClient;
}

/**
 * Check if QStash is available (token is configured).
 */
export function isQstashAvailable(): boolean {
  return Boolean(getServerEnvVarWithFallback("QSTASH_TOKEN", ""));
}

// ===== HELPERS =====

/**
 * Parse a delay string (e.g., "10s", "5m") to seconds.
 *
 * @throws Error if the delay string format is invalid
 */
function parseDelayToSeconds(delay: string): number {
  type DelayUnit = "s" | "m" | "h" | "d";

  const match = delay.match(/^(\d+)(s|m|h|d)?$/);
  if (!match) {
    throw new Error(
      `Invalid delay format: "${delay}". Expected format: <number>[s|m|h|d] (e.g., "10s", "5m", "1h", "1d")`
    );
  }

  const value = parseInt(match[1], 10);
  const unit = (match[2] ?? "s") as DelayUnit;

  switch (unit) {
    case "s":
      return value;
    case "m":
      return value * 60;
    case "h":
      return value * 3600;
    case "d":
      return value * 86400;
  }

  const exhaustiveCheck: never = unit;
  return exhaustiveCheck;
}

// ===== JOB ENQUEUE =====

/**
 * Options for enqueuing a job.
 */
export interface EnqueueJobOptions {
  /** Deduplication ID to prevent duplicate jobs (optional) */
  deduplicationId?: string;
  /** Delay before first delivery in seconds */
  delay?: number;
  /** Override default retry count */
  retries?: number;
}

/**
 * Result of a successful job enqueue.
 */
export interface EnqueueJobResult {
  /** QStash message ID for tracking */
  messageId: string;
}

/**
 * Enqueue a job to a QStash-backed worker endpoint.
 *
 * Enforces ADR-0048 retry policy:
 * - 5 retries (6 total attempts)
 * - Exponential backoff starting at 10s
 *
 * @param jobType - Type identifier for the job (used in telemetry)
 * @param payload - Job payload to deliver
 * @param path - Worker endpoint path (e.g., "/api/jobs/notify-collaborators")
 * @param options - Optional enqueue configuration
 * @returns EnqueueJobResult with messageId, or null if QStash unavailable
 *
 * @example
 * ```ts
 * const result = await enqueueJob(
 *   "notify-collaborators",
 *   { eventKey, payload },
 *   "/api/jobs/notify-collaborators"
 * );
 * if (result) {
 *   console.log("Enqueued:", result.messageId);
 * }
 * ```
 */
export async function enqueueJob(
  jobType: string,
  payload: unknown,
  path: string,
  options: EnqueueJobOptions = {}
): Promise<EnqueueJobResult | null> {
  return await withTelemetrySpan(
    "qstash.enqueue",
    {
      attributes: {
        "qstash.job_type": jobType,
        "qstash.path": path,
        "qstash.retries": options.retries ?? QSTASH_RETRY_CONFIG.retries,
      },
    },
    async (span) => {
      const client = getQstashClient();
      if (!client) {
        span.setAttribute("qstash.unavailable", true);
        return null;
      }

      // Get origin for building full URL
      const origin = getServerEnvVarWithFallback("NEXT_PUBLIC_SITE_URL", "");
      if (!origin) {
        span.setAttribute("qstash.missing_origin", true);
        recordTelemetryEvent("qstash.missing_origin", {
          attributes: { jobType, path },
          level: "warning",
        });
        throw new Error(
          "NEXT_PUBLIC_SITE_URL is not configured; cannot enqueue QStash job"
        );
      }
      const url = `${origin}${path}`;
      span.setAttribute("qstash.url", url);

      // Deduplication is caller-controlled; random IDs defeat dedup purpose
      const deduplicationId = options.deduplicationId;
      if (deduplicationId) {
        span.setAttribute("qstash.dedup_id", deduplicationId);
      } else {
        span.setAttribute("qstash.dedup_id_missing", true);
      }

      // Parse delay from config (e.g., "10s" -> 10)
      const defaultDelay = parseDelayToSeconds(QSTASH_RETRY_CONFIG.delay);

      // Publish with enforced retry policy from ADR-0048
      const response = await client.publishJSON({
        body: payload,
        deduplicationId,
        delay: options.delay ?? defaultDelay,
        retries: options.retries ?? QSTASH_RETRY_CONFIG.retries,
        url,
      });

      // Handle response - messageId is present on PublishToUrlResponse
      const messageId = response.messageId;
      span.setAttribute("qstash.message_id", messageId);

      return { messageId };
    }
  );
}

/**
 * Enqueue a job with error handling that returns success/failure status.
 *
 * Unlike `enqueueJob`, this function catches errors and returns a result
 * object suitable for handlers that need to implement fallback behavior.
 *
 * @param jobType - Type identifier for the job
 * @param payload - Job payload to deliver
 * @param path - Worker endpoint path
 * @param options - Optional enqueue configuration
 * @returns Object with success status and optional error/messageId
 */
export async function tryEnqueueJob(
  jobType: string,
  payload: unknown,
  path: string,
  options: EnqueueJobOptions = {}
): Promise<
  { success: true; messageId: string } | { success: false; error: Error | null }
> {
  try {
    const result = await enqueueJob(jobType, payload, path, options);
    if (result) {
      return { messageId: result.messageId, success: true };
    }
    return { error: null, success: false };
  } catch (error) {
    return { error: error instanceof Error ? error : null, success: false };
  }
}
