/**
 * @fileoverview Shared QStash client with enforced retry policy per ADR-0048.
 *
 * Centralizes QStash job enqueuing to ensure consistent retry configuration
 * across all webhook handlers. Implements policy defined in ADR-0048:
 * - 5 retries (6 total attempts)
 * - Exponential backoff starting at 10s
 */

import "server-only";

import { Client } from "@upstash/qstash";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { QSTASH_RETRY_CONFIG } from "./config";

// ===== CLIENT SINGLETON =====

let qstashClient: Client | null = null;

/**
 * Get or create the QStash client singleton.
 *
 * @returns QStash client or null if QSTASH_TOKEN is not configured
 */
export function getQstashClient(): Client | null {
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
 */
function parseDelayToSeconds(delay: string): number {
  const match = delay.match(/^(\d+)(s|m|h|d)?$/);
  if (!match) return 10; // Default to 10 seconds

  const value = parseInt(match[1], 10);
  const unit = match[2] || "s";

  switch (unit) {
    case "s":
      return value;
    case "m":
      return value * 60;
    case "h":
      return value * 3600;
    case "d":
      return value * 86400;
    default:
      return value;
  }
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
        return null;
      }
      const url = `${origin}${path}`;
      span.setAttribute("qstash.url", url);

      // Build deduplication ID if not provided
      const deduplicationId = options.deduplicationId ?? `${jobType}:${Date.now()}`;
      span.setAttribute("qstash.dedup_id", deduplicationId);

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

      // Handle response - messageId exists on PublishToUrlResponse
      const messageId = "messageId" in response ? response.messageId : "unknown";
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
