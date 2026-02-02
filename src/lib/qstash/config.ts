/**
 * @fileoverview QStash configuration constants.
 */

import "server-only";

/**
 * QStash retry configuration for webhook job handlers.
 *
 * Notes:
 * - `delay` controls the initial delivery delay for the message.
 * - `retryDelay` controls the retry backoff (in milliseconds) via `Upstash-Retry-Delay`.
 * - `retried` in the expression is the retry attempt count starting from 0.
 */
export const QSTASH_RETRY_CONFIG = {
  /** Default delay before first delivery (seconds string) */
  delay: "10s",
  /** Number of retry attempts after initial failure */
  retries: 5,
  /** Exponential backoff starting at 10 seconds (milliseconds expression) */
  retryDelay: "10000 * pow(2, retried)",
} as const;

/** QStash signing key header name */
export const QSTASH_SIGNATURE_HEADER = "Upstash-Signature" as const;

/** QStash message identifier header (stable across retries) */
export const QSTASH_MESSAGE_ID_HEADER = "Upstash-Message-Id" as const;

/** QStash retry counter header (number of retries already performed) */
export const QSTASH_RETRIED_HEADER = "Upstash-Retried" as const;

/**
 * QStash non-retryable error header.
 * When paired with HTTP 489, QStash stops retries and forwards to DLQ (if configured).
 */
export const QSTASH_NONRETRYABLE_ERROR_HEADER = "Upstash-NonRetryable-Error" as const;

/** QStash deduplication id header (publishing) */
export const QSTASH_DEDUPLICATION_ID_HEADER = "Upstash-Deduplication-Id" as const;

/** QStash content-based deduplication toggle header (publishing) */
export const QSTASH_CONTENT_BASED_DEDUP_HEADER =
  "Upstash-Content-Based-Deduplication" as const;

/**
 * Canonical job labels for QStash message filtering, DLQ queries, and cancellation.
 */
export const QSTASH_JOB_LABELS = {
  // biome-ignore lint/style/useNamingConvention: QStash labels are constants
  ATTACHMENTS_INGEST: "tripsage:attachments-ingest",
  // biome-ignore lint/style/useNamingConvention: QStash labels are constants
  MEMORY_SYNC: "tripsage:memory-sync",
  // biome-ignore lint/style/useNamingConvention: QStash labels are constants
  NOTIFY_COLLABORATORS: "tripsage:notify-collaborators",
  // biome-ignore lint/style/useNamingConvention: QStash labels are constants
  RAG_INDEX: "tripsage:rag-index",
} as const;

/**
 * Union type of all valid QStash job label values.
 */
// biome-ignore lint/style/useNamingConvention: keep QStash casing
export type QStashJobLabel = (typeof QSTASH_JOB_LABELS)[keyof typeof QSTASH_JOB_LABELS];
