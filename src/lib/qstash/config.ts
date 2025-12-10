/**
 * @fileoverview QStash configuration constants per ADR-0048.
 */

/**
 * QStash retry configuration for webhook job handlers.
 * Max 6 total attempts (1 initial + 5 retries) with exponential backoff.
 */
export const QSTASH_RETRY_CONFIG = {
  /** Initial delay before first retry (QStash uses exponential backoff) */
  delay: "10s",
  /** Number of retry attempts after initial failure */
  retries: 5,
} as const;

/** Redis key prefix for dead letter queue entries */
export const DLQ_KEY_PREFIX = "qstash-dlq" as const;

/** TTL for DLQ entries in seconds (7 days) */
export const DLQ_TTL_SECONDS = 60 * 60 * 24 * 7;

/** Maximum number of DLQ entries to keep per job type */
export const DLQ_MAX_ENTRIES = 1000;

/** QStash signing key header name */
export const QSTASH_SIGNATURE_HEADER = "upstash-signature" as const;
