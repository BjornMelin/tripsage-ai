/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchWithRetry, type RetryOptions, retryWithBackoff } from "../retry";

describe("retryWithBackoff", () => {
  // Use real timers with minimal delays for simpler async behavior
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("succeeds on first attempt without retries", async () => {
    const fn = vi.fn().mockResolvedValue("success");
    const options: RetryOptions = {
      attempts: 3,
      baseDelayMs: 1,
    };

    const result = await retryWithBackoff(fn, options);

    expect(result).toBe("success");
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith(1);
  });

  it("retries on failure and succeeds on subsequent attempt", async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new Error("Attempt 1 failed"))
      .mockResolvedValue("success");

    const options: RetryOptions = {
      attempts: 3,
      baseDelayMs: 1,
    };

    const result = await retryWithBackoff(fn, options);

    expect(result).toBe("success");
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenNthCalledWith(1, 1);
    expect(fn).toHaveBeenNthCalledWith(2, 2);
  });

  it("throws last error after exhausting all attempts", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("Always fails"));
    const options: RetryOptions = {
      attempts: 3,
      baseDelayMs: 1,
    };

    await expect(retryWithBackoff(fn, options)).rejects.toThrow("Always fails");
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it("respects isRetryable predicate", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("Non-retryable error"));
    const options: RetryOptions = {
      attempts: 3,
      baseDelayMs: 1,
      isRetryable: () => false,
    };

    await expect(retryWithBackoff(fn, options)).rejects.toThrow("Non-retryable error");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("calls isRetryable with error and attempt number", async () => {
    const isRetryable = vi.fn().mockReturnValue(true);
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new Error("Error 1"))
      .mockResolvedValue("success");

    const options: RetryOptions = {
      attempts: 3,
      baseDelayMs: 1,
      isRetryable,
    };

    await retryWithBackoff(fn, options);

    expect(isRetryable).toHaveBeenCalledWith(expect.any(Error), 1);
  });

  it("calls onRetry hook before each retry attempt", async () => {
    const onRetry = vi.fn();
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new Error("Attempt 1 failed"))
      .mockRejectedValueOnce(new Error("Attempt 2 failed"))
      .mockResolvedValue("success");

    const options: RetryOptions = {
      attempts: 4,
      baseDelayMs: 1,
      jitterRatio: 0,
      onRetry,
    };

    await retryWithBackoff(fn, options);

    expect(onRetry).toHaveBeenCalledTimes(2);
    expect(onRetry).toHaveBeenNthCalledWith(1, {
      attempt: 1,
      delayMs: 1,
      error: expect.any(Error),
    });
    expect(onRetry).toHaveBeenNthCalledWith(2, {
      attempt: 2,
      delayMs: 2,
      error: expect.any(Error),
    });
  });

  it("applies exponential backoff to delays", async () => {
    const onRetry = vi.fn();
    const fn = vi.fn().mockRejectedValue(new Error("Always fails"));

    const options: RetryOptions = {
      attempts: 4,
      baseDelayMs: 10,
      jitterRatio: 0,
      onRetry,
    };

    await expect(retryWithBackoff(fn, options)).rejects.toThrow("Always fails");

    expect(onRetry).toHaveBeenCalledTimes(3);
    const delays = onRetry.mock.calls.map((call) => call[0].delayMs);
    expect(delays).toEqual([10, 20, 40]); // 10*2^0, 10*2^1, 10*2^2
  });

  it("caps delay at maxDelayMs", async () => {
    const onRetry = vi.fn();
    const fn = vi.fn().mockRejectedValue(new Error("Always fails"));

    const options: RetryOptions = {
      attempts: 5,
      baseDelayMs: 10,
      jitterRatio: 0,
      maxDelayMs: 30,
      onRetry,
    };

    await expect(retryWithBackoff(fn, options)).rejects.toThrow("Always fails");

    const delays = onRetry.mock.calls.map((call) => call[0].delayMs);
    expect(delays).toEqual([10, 20, 30, 30]); // Capped at 30
  });

  it("applies jitter to delays within expected range", async () => {
    const onRetry = vi.fn();
    const fn = vi.fn().mockRejectedValue(new Error("Always fails"));

    const options: RetryOptions = {
      attempts: 3,
      baseDelayMs: 100,
      jitterRatio: 0.5,
      onRetry,
    };

    await expect(retryWithBackoff(fn, options)).rejects.toThrow("Always fails");

    const delays = onRetry.mock.calls.map((call) => call[0].delayMs);
    // With 50% jitter on base 100ms, range is [75, 125]
    expect(delays[0]).toBeGreaterThanOrEqual(75);
    expect(delays[0]).toBeLessThanOrEqual(125);
  });

  it("wraps non-Error throws in Error", async () => {
    const fn = vi.fn().mockRejectedValue("string error");
    const options: RetryOptions = {
      attempts: 1,
      baseDelayMs: 1,
    };

    await expect(retryWithBackoff(fn, options)).rejects.toThrow(
      "retry_with_backoff_failed"
    );
  });
});

describe("fetchWithRetry", () => {
  // fetchWithRetry tests use real timers since function has internal timeout logic
  // Using minimal backoff to keep tests fast
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("returns response on successful fetch", async () => {
    const mockResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
    });
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    const result = await fetchWithRetry("https://api.example.com/data", {});

    expect(result).toBe(mockResponse);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("retries on network errors and succeeds", async () => {
    const mockResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
    });
    global.fetch = vi
      .fn()
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValue(mockResponse);

    const result = await fetchWithRetry(
      "https://api.example.com/data",
      {},
      { backoffMs: 1, retries: 1 }
    );

    expect(result).toBe(mockResponse);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it("throws error with code after exhausting retries", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

    await expect(
      fetchWithRetry("https://api.example.com/data", {}, { backoffMs: 1, retries: 1 })
    ).rejects.toMatchObject({
      code: "fetch_failed",
      message: "fetch_failed",
      meta: {
        attempt: 2,
        maxRetries: 1,
        url: "https://api.example.com/data",
      },
    });
  });

  it("throws timeout error when request aborts", async () => {
    const abortError = new Error("Aborted");
    abortError.name = "AbortError";
    global.fetch = vi.fn().mockRejectedValue(abortError);

    await expect(
      fetchWithRetry("https://api.example.com/data", {}, { timeoutMs: 100 })
    ).rejects.toMatchObject({
      code: "fetch_timeout",
      message: "fetch_timeout",
    });
  });

  it("does not retry on timeout errors", async () => {
    const abortError = new Error("Aborted");
    abortError.name = "AbortError";
    global.fetch = vi.fn().mockRejectedValue(abortError);

    await expect(
      fetchWithRetry("https://api.example.com/data", {}, { backoffMs: 1, retries: 3 })
    ).rejects.toThrow();

    // Should only call fetch once since timeout errors are not retryable
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("passes request options to fetch", async () => {
    const mockResponse = new Response(JSON.stringify({ created: true }), {
      status: 201,
    });
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    await fetchWithRetry("https://api.example.com/data", {
      body: JSON.stringify({ name: "test" }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "https://api.example.com/data",
      expect.objectContaining({
        body: JSON.stringify({ name: "test" }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      })
    );
  });

  it("handles caller abort signal", async () => {
    const controller = new AbortController();
    const abortError = new Error("Aborted by caller");
    abortError.name = "AbortError";

    global.fetch = vi.fn().mockRejectedValue(abortError);
    controller.abort();

    await expect(
      fetchWithRetry("https://api.example.com/data", {
        signal: controller.signal,
      })
    ).rejects.toMatchObject({
      code: "fetch_timeout",
    });
  });
});
