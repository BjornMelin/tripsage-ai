/**
 * @fileoverview Lightweight retry helper with exponential backoff and jitter.
 */

import { randomInt } from "node:crypto";

/**
 * Retry configuration for {@link retryWithBackoff}.
 */
export type RetryOptions = {
  /** Maximum attempts including the initial call. */
  attempts: number;
  /** Base delay in milliseconds for backoff (attempt 1 waits baseDelayMs). */
  baseDelayMs: number;
  /** Optional cap for delay. */
  maxDelayMs?: number;
  /** Jitter ratio (0-1) to randomize delays. */
  jitterRatio?: number;
  /** Predicate to decide if an error is retryable. */
  isRetryable?: (error: unknown, attempt: number) => boolean;
  /** Hook invoked before each retry attempt. */
  onRetry?: (info: { attempt: number; delayMs: number; error: unknown }) => void;
};

const DEFAULT_JITTER_RATIO = 0.25;

/**
 * Executes an async function with bounded retries and backoff jitter.
 *
 * @param fn Function to execute.
 * @param options Retry configuration.
 * @returns Result of fn if successful.
 * @throws Last error after exhausting retries.
 */
export async function retryWithBackoff<T>(
  fn: (attempt: number) => Promise<T>,
  options: RetryOptions
): Promise<T> {
  const {
    attempts,
    baseDelayMs,
    maxDelayMs,
    jitterRatio = DEFAULT_JITTER_RATIO,
    isRetryable = () => true,
    onRetry,
  } = options;

  let attempt = 0;
  let lastError: unknown;

  while (attempt < attempts) {
    try {
      return await fn(attempt + 1);
    } catch (error) {
      lastError = error;
      attempt += 1;

      const shouldRetry = attempt < attempts && isRetryable(error, attempt);
      if (!shouldRetry) {
        break;
      }

      const backoff = calculateDelay({
        attempt,
        baseDelayMs,
        jitterRatio,
        maxDelayMs,
      });
      if (onRetry) {
        onRetry({ attempt, delayMs: backoff, error });
      }
      await delay(backoff);
    }
  }

  throw lastError instanceof Error ? lastError : new Error("retry_with_backoff_failed");
}

function calculateDelay(params: {
  attempt: number;
  baseDelayMs: number;
  maxDelayMs?: number;
  jitterRatio: number;
}): number {
  const raw = params.baseDelayMs * 2 ** (params.attempt - 1);
  const capped = params.maxDelayMs ? Math.min(raw, params.maxDelayMs) : raw;
  const jitterRange = Math.floor(capped * params.jitterRatio);
  if (jitterRange <= 0) return capped;
  const jitter = randomInt(0, jitterRange + 1);
  return capped - jitterRange / 2 + jitter;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
