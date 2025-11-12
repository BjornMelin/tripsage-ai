/**
 * @fileoverview HTTP fetch utility with timeout and retry logic.
 *
 * Uses AbortController for timeouts and exponential backoff for retries.
 * Provides consistent error handling with domain-specific error codes.
 */

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
 * Implements exponential backoff between retry attempts. Throws errors with
 * `code` and `meta` properties for consistent error handling.
 *
 * @param url - The URL to fetch.
 * @param init - Fetch options (RequestInit).
 * @param options - Retry and timeout options.
 * @returns The Response object on success.
 * @throws {Error} Error with `code` property set to "fetch_timeout" or "fetch_failed",
 *   and `meta` property containing attempt details.
 */
export async function fetchWithRetry(
  url: string,
  init: RequestInit,
  options: FetchRetryOptions = {}
): Promise<Response> {
  const { timeoutMs = 12000, retries = 2, backoffMs = 100 } = options;
  for (let attempt = 0; attempt <= retries; attempt++) {
    // Fresh controller and timeout for each attempt
    const controller = new AbortController();
    // Propagate caller aborts to our controller (no AbortSignal.any dependency)
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
      if (attempt === retries) {
        const isTimeout = err instanceof Error && err.name === "AbortError";
        const error: Error & { code?: string; meta?: Record<string, unknown> } =
          new Error(isTimeout ? "fetch_timeout" : "fetch_failed");
        error.code = isTimeout ? "fetch_timeout" : "fetch_failed";
        error.meta = { attempt: attempt + 1, maxRetries: retries, url };
        throw error;
      }
      // Exponential backoff: backoffMs * 2^attempt
      const delayMs = backoffMs * 2 ** attempt;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
  throw new Error("fetch_failed");
}
