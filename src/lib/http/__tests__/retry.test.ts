/** @vitest-environment node */

import { delay, HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
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
  const ApiUrl = "https://api.example.com/data";

  it("returns response on successful fetch", async () => {
    server.use(
      http.get(ApiUrl, () => {
        return HttpResponse.json({ data: "test" }, { status: 200 });
      })
    );

    const result = await fetchWithRetry(ApiUrl, {});
    expect(result.status).toBe(200);
    await expect(result.json()).resolves.toEqual({ data: "test" });
  });

  it("retries on network errors and succeeds", async () => {
    let calls = 0;
    server.use(
      http.get(ApiUrl, () => {
        calls += 1;
        if (calls === 1) {
          return HttpResponse.error();
        }
        return HttpResponse.json({ data: "test" }, { status: 200 });
      })
    );

    const result = await fetchWithRetry(ApiUrl, {}, { backoffMs: 1, retries: 1 });
    expect(calls).toBe(2);
    await expect(result.json()).resolves.toEqual({ data: "test" });
  });

  it("throws error with code after exhausting retries", async () => {
    let calls = 0;
    server.use(
      http.get(ApiUrl, () => {
        calls += 1;
        return HttpResponse.error();
      })
    );

    await expect(
      fetchWithRetry(ApiUrl, {}, { backoffMs: 1, retries: 1 })
    ).rejects.toMatchObject({
      code: "fetch_failed",
      message: "fetch_failed",
      meta: {
        attempt: 2,
        maxRetries: 1,
        url: ApiUrl,
      },
    });
    expect(calls).toBe(2);
  });

  it("throws timeout error when request aborts", async () => {
    server.use(
      http.get(ApiUrl, async () => {
        await delay(50);
        return HttpResponse.json({ data: "late" }, { status: 200 });
      })
    );

    await expect(fetchWithRetry(ApiUrl, {}, { timeoutMs: 10 })).rejects.toMatchObject({
      code: "fetch_timeout",
      message: "fetch_timeout",
    });
  });

  it("does not retry on timeout errors", async () => {
    let calls = 0;
    server.use(
      http.get(ApiUrl, async () => {
        calls += 1;
        await delay(50);
        return HttpResponse.json({ data: "late" }, { status: 200 });
      })
    );

    await expect(
      fetchWithRetry(ApiUrl, {}, { backoffMs: 1, retries: 3, timeoutMs: 10 })
    ).rejects.toThrow();

    // Should only attempt once since timeout errors are not retryable
    expect(calls).toBe(1);
  });

  it("passes request options to fetch", async () => {
    const requests: Request[] = [];
    server.use(
      http.post(ApiUrl, ({ request }) => {
        requests.push(request);
        return HttpResponse.json({ created: true }, { status: 201 });
      })
    );

    await fetchWithRetry(ApiUrl, {
      body: JSON.stringify({ name: "test" }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });

    expect(requests).toHaveLength(1);
    await expect(requests[0].text()).resolves.toBe(JSON.stringify({ name: "test" }));
    expect(requests[0].method).toBe("POST");
    expect(requests[0].headers.get("content-type")).toContain("application/json");
  });

  it("handles caller abort signal", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(
      fetchWithRetry(ApiUrl, {
        signal: controller.signal,
      })
    ).rejects.toMatchObject({
      code: "fetch_timeout",
    });
  });
});
