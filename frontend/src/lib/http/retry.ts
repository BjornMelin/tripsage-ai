/**
 * @fileoverview Lightweight retry helper with exponential backoff and jitter.
 */

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
  const jitter = Math.floor(Math.random() * (jitterRange + 1));
  return capped - jitterRange / 2 + jitter;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

/**
 * Options for fetch retry behavior.
 */
export type FetchRetryOptions = {
  /**
   * Timeout in milliseconds. Default: 12000.
   */
  timeoutMs?: number;
  /**
   * Maximum number of retries (attempts = retries + 1). Default: 2.
   */
  retries?: number;
  /**
   * Base backoff delay in milliseconds. Actual delay is backoffMs * 2^attempt.
   * Default: 100.
   */
  backoffMs?: number;
};

/**
 * Fetch with timeout and retries.
 *
 * Implements exponential backoff between retry attempts using retryWithBackoff.
 * Throws errors with `code` and `meta` properties for consistent error handling.
 *
 * @param url - The URL to fetch.
 * @param init - Fetch options (RequestInit).
 * @param options - Retry and timeout options.
 * @returns The Response object on success.
 * @throws {Error} Error with `code` property set to "fetch_timeout" or "fetch_failed",
 *   and `meta` property containing attempt details.
 */
export function fetchWithRetry(
  url: string,
  init: RequestInit,
  options: FetchRetryOptions = {}
): Promise<Response> {
  const { timeoutMs = 12000, retries = 2, backoffMs = 100 } = options;
  const attempts = retries + 1;

  return retryWithBackoff(
    async (attemptNumber) => {
      // Fresh controller and timeout for each attempt
      const controller = new AbortController();
      // Propagate caller aborts to our controller
      let onCallerAbort: (() => void) | undefined;
      if (init.signal) {
        if (init.signal.aborted) {
          controller.abort();
        } else {
          onCallerAbort = () => controller.abort();
          init.signal.addEventListener("abort", onCallerAbort, { once: true });
        }
      }
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const res = await fetch(url, {
          ...init,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (init.signal && onCallerAbort) {
          init.signal.removeEventListener("abort", onCallerAbort);
        }
        return res;
      } catch (err) {
        clearTimeout(timeoutId);
        if (init.signal && onCallerAbort) {
          init.signal.removeEventListener("abort", onCallerAbort);
        }
        const isTimeout = err instanceof Error && err.name === "AbortError";
        const error: Error & { code?: string; meta?: Record<string, unknown> } =
          new Error(isTimeout ? "fetch_timeout" : "fetch_failed");
        error.code = isTimeout ? "fetch_timeout" : "fetch_failed";
        error.meta = { attempt: attemptNumber, maxRetries: retries, url };
        throw error;
      }
    },
    {
      attempts,
      baseDelayMs: backoffMs,
      isRetryable: (error) => {
        // Don't retry on timeout errors or abort errors
        if (error instanceof Error) {
          const errorCode = (error as { code?: string }).code;
          if (error.name === "AbortError" || errorCode === "fetch_timeout") {
            return false;
          }
        }
        return true;
      },
    }
  );
}
