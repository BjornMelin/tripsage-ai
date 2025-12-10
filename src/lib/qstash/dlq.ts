/**
 * @fileoverview Dead Letter Queue (DLQ) implementation for failed QStash jobs.
 *
 * Per ADR-0048, failed jobs after max retries are stored in Redis for later review.
 * Implements:
 * - Payload sanitization to prevent PII exposure
 * - Alerting via telemetry events for monitoring
 * - Atomic LREM operations for thread-safe removal
 * - Error stack trace preservation for debugging
 */

import "server-only";

import { z } from "zod";
import { getRedis } from "@/lib/redis";
import { nowIso, secureUuid } from "@/lib/security/random";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";
import { DLQ_KEY_PREFIX, DLQ_MAX_ENTRIES, DLQ_TTL_SECONDS } from "./config";

// ===== CONSTANTS =====

/**
 * Threshold for critical alerts - when DLQ count exceeds this, emit critical event.
 */
const DLQ_ALERT_THRESHOLD = 100;

/**
 * Sensitive field names to redact from payloads before storing in DLQ.
 * These patterns protect PII and credentials if Redis is compromised.
 */
const SENSITIVE_FIELDS = [
  "email",
  "password",
  "token",
  "api_key",
  "apiKey",
  "secret",
  "ssn",
  "credit_card",
  "creditCard",
  "phone",
  "address",
] as const;

// ===== SCHEMAS =====

/**
 * Schema for a DLQ entry stored in Redis.
 */
export const dlqEntrySchema = z.strictObject({
  /** Number of attempts made before final failure */
  attempts: z.number().int().positive(),
  /** Error message or stringified error */
  error: z.string(),
  /** Error code if available (e.g., "ECONNREFUSED") */
  errorCode: z.string().optional(),
  /** Error stack trace for debugging */
  errorStack: z.string().optional(),
  /** ISO timestamp when the job was moved to DLQ */
  failedAt: z.string(),
  /** Unique identifier for this DLQ entry */
  id: z.string().min(1),
  /** Type of job that failed (e.g., "notify-collaborators") */
  jobType: z.string().min(1),
  /** Original job payload (sanitized to remove PII) */
  payload: z.unknown(),
});

// biome-ignore lint/style/useNamingConvention: DLQ is established acronym for Dead Letter Queue
export type DLQEntry = z.infer<typeof dlqEntrySchema>;

// ===== DLQ OPERATIONS =====

/**
 * Push a failed job to the Dead Letter Queue in Redis.
 *
 * Implements:
 * - Payload sanitization to redact PII before storage
 * - Alerting via telemetry events for monitoring
 * - Error stack trace storage for debugging
 *
 * @param jobType - Type of job (e.g., "notify-collaborators", "memory-sync")
 * @param payload - Original job payload (will be sanitized)
 * @param error - Error message or object
 * @param attempts - Number of attempts made
 * @return Promise resolving to the DLQ entry ID, or null if Redis unavailable
 */
// biome-ignore lint/style/useNamingConvention: DLQ is established acronym for Dead Letter Queue
export async function pushToDLQ(
  jobType: string,
  payload: unknown,
  error: unknown,
  attempts: number
): Promise<string | null> {
  return await withTelemetrySpan(
    "qstash.dlq.push",
    {
      attributes: {
        "dlq.attempts": attempts,
        "dlq.job_type": jobType,
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("dlq.redis_unavailable", true);
        return null;
      }

      const entryId = secureUuid();

      // Extract error details including stack trace
      const errorMessage = error instanceof Error ? error.message : String(error);
      const errorStack = error instanceof Error ? error.stack : undefined;
      const errorCode = (error as { code?: string })?.code;

      // Sanitize payload to prevent PII exposure
      const sanitizedPayload = sanitizePayloadForDlq(payload);

      const entry: DLQEntry = {
        attempts,
        error: errorMessage,
        errorCode,
        errorStack,
        failedAt: nowIso(),
        id: entryId,
        jobType,
        payload: sanitizedPayload,
      };

      const key = `${DLQ_KEY_PREFIX}:${jobType}`;
      span.setAttribute("dlq.key", key);
      span.setAttribute("dlq.entry_id", entryId);

      // Use LPUSH to add to front of list (most recent first)
      await redis.lpush(key, JSON.stringify(entry));

      // Trim list to max entries to prevent unbounded growth
      await redis.ltrim(key, 0, DLQ_MAX_ENTRIES - 1);

      // Set TTL on the list (refreshed on each push)
      await redis.expire(key, DLQ_TTL_SECONDS);

      span.setAttribute("qstash.dlq", true);

      // Emit alerting event for observability
      recordTelemetryEvent("qstash.dlq_entry_created", {
        attributes: {
          "dlq.attempts": attempts,
          "dlq.entry_id": entryId,
          "dlq.job_type": jobType,
        },
        level: "warning",
      });

      // Check threshold and emit critical alert
      const count = await getDLQCount(jobType);
      if (count > DLQ_ALERT_THRESHOLD) {
        recordTelemetryEvent("qstash.dlq_threshold_exceeded", {
          attributes: {
            "dlq.count": count,
            "dlq.job_type": jobType,
            "dlq.threshold": DLQ_ALERT_THRESHOLD,
          },
          level: "error",
        });
        span.setAttribute("dlq.threshold_exceeded", true);
        span.setAttribute("dlq.count", count);
      }

      return entryId;
    }
  );
}

/**
 * List DLQ entries for a specific job type or all types.
 *
 * @param jobType - Filter by job type (optional, lists all if not provided)
 * @param limit - Maximum entries to return (default 100)
 * @return Promise resolving to array of DLQ entries
 */
// biome-ignore lint/style/useNamingConvention: DLQ is established acronym for Dead Letter Queue
export async function listDLQEntries(
  jobType?: string,
  limit = 100
): Promise<DLQEntry[]> {
  return await withTelemetrySpan(
    "qstash.dlq.list",
    {
      attributes: {
        "dlq.job_type": jobType ?? "all",
        "dlq.limit": limit,
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("dlq.redis_unavailable", true);
        return [];
      }

      const entries: DLQEntry[] = [];

      if (jobType) {
        // Single job type query
        const key = `${DLQ_KEY_PREFIX}:${jobType}`;
        const raw = await redis.lrange(key, 0, limit - 1);
        for (const item of raw) {
          const parsed = parseDlqEntry(item);
          if (parsed) entries.push(parsed);
        }
      } else {
        // Scan all DLQ keys (pattern: qstash-dlq:*)
        const pattern = `${DLQ_KEY_PREFIX}:*`;
        let cursor = 0;
        const perTypeLimit = Math.ceil(limit / 5); // Distribute limit across types

        do {
          const [nextCursor, keys] = await redis.scan(cursor, {
            count: 100,
            match: pattern,
          });
          cursor = Number(nextCursor);

          for (const key of keys) {
            if (entries.length >= limit) break;
            const raw = await redis.lrange(
              key,
              0,
              Math.min(perTypeLimit, limit - entries.length) - 1
            );
            for (const item of raw) {
              if (entries.length >= limit) break;
              const parsed = parseDlqEntry(item);
              if (parsed) entries.push(parsed);
            }
          }
        } while (cursor !== 0 && entries.length < limit);
      }

      span.setAttribute("dlq.count", entries.length);
      return entries;
    }
  );
}

/**
 * Remove a specific DLQ entry by ID.
 *
 * Uses atomic LREM operation to prevent race conditions during concurrent
 * removals. The previous read-modify-write pattern could lose entries
 * when multiple workers processed the same list.
 *
 * @param jobType - Job type the entry belongs to
 * @param entryId - Entry ID to remove
 * @return Promise resolving to true if removed, false otherwise
 */
// biome-ignore lint/style/useNamingConvention: DLQ is established acronym for Dead Letter Queue
export async function removeDLQEntry(
  jobType: string,
  entryId: string
): Promise<boolean> {
  return await withTelemetrySpan(
    "qstash.dlq.remove",
    {
      attributes: {
        "dlq.entry_id": entryId,
        "dlq.job_type": jobType,
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("dlq.redis_unavailable", true);
        return false;
      }

      const key = `${DLQ_KEY_PREFIX}:${jobType}`;

      // Find the entry to get its exact serialized form for LREM
      const entries = await redis.lrange(key, 0, -1);

      for (const entryStr of entries) {
        try {
          const entry = parseDlqEntry(entryStr);
          if (entry?.id === entryId) {
            // Use atomic LREM to remove exactly this serialized entry
            // This is thread-safe: concurrent removals won't lose other entries
            const removed = await redis.lrem(
              key,
              1,
              typeof entryStr === "string" ? entryStr : JSON.stringify(entryStr)
            );
            const success = removed > 0;
            span.setAttribute("dlq.removed", success);
            return success;
          }
        } catch {
          // Skip entries that fail to parse - corrupted data
        }
      }

      span.setAttribute("dlq.removed", false);
      span.setAttribute("dlq.entry_not_found", true);
      return false;
    }
  );
}

/**
 * Get the count of DLQ entries for a job type.
 *
 * @param jobType - Job type to count
 * @return Promise resolving to entry count
 */
// biome-ignore lint/style/useNamingConvention: DLQ is established acronym for Dead Letter Queue
export async function getDLQCount(jobType: string): Promise<number> {
  const redis = getRedis();
  if (!redis) return 0;

  const key = `${DLQ_KEY_PREFIX}:${jobType}`;
  return await redis.llen(key);
}

// ===== HELPERS =====

/**
 * Parse a raw DLQ entry from Redis.
 *
 * @param raw - Raw entry from Redis (string or object)
 * @return Parsed DLQ entry or null if invalid
 */
function parseDlqEntry(raw: unknown): DLQEntry | null {
  try {
    const obj = typeof raw === "string" ? JSON.parse(raw) : raw;
    const result = dlqEntrySchema.safeParse(obj);
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}

/**
 * Sanitize a payload before storing in DLQ to prevent PII exposure.
 *
 * Recursively redacts sensitive fields like email, password, token, etc.
 * This protects user data if the Redis instance is ever compromised.
 *
 * @param payload - Raw payload to sanitize
 * @return Sanitized payload with sensitive fields redacted
 */
function sanitizePayloadForDlq(payload: unknown): unknown {
  if (payload === null || payload === undefined) {
    return payload;
  }

  if (Array.isArray(payload)) {
    return payload.map(sanitizePayloadForDlq);
  }

  if (typeof payload !== "object") {
    return payload;
  }

  const sanitized: Record<string, unknown> = {};
  const obj = payload as Record<string, unknown>;

  for (const [key, value] of Object.entries(obj)) {
    const lowerKey = key.toLowerCase();

    // Check if this key matches any sensitive field pattern
    const isSensitive = SENSITIVE_FIELDS.some(
      (field) =>
        lowerKey === field.toLowerCase() || lowerKey.includes(field.toLowerCase())
    );

    if (isSensitive && value !== undefined && value !== null) {
      sanitized[key] = "[REDACTED]";
    } else if (typeof value === "object" && value !== null) {
      // Recursively sanitize nested objects (including record/old_record)
      sanitized[key] = sanitizePayloadForDlq(value);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}
