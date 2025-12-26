/** @vitest-environment node */

import { Ratelimit } from "@upstash/ratelimit";
import { beforeEach, describe, expect, it, vi } from "vitest";

const GET_ENV_VAR = vi.hoisted(() => vi.fn());
const GET_ENV_VAR_FALLBACK = vi.hoisted(() => vi.fn());
const GET_REDIS = vi.hoisted(() => vi.fn());
const RECORD_EVENT = vi.hoisted(() => vi.fn());

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: GET_ENV_VAR,
  getServerEnvVarWithFallback: GET_ENV_VAR_FALLBACK,
}));

vi.mock("@/lib/redis", () => ({
  getRedis: GET_REDIS,
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: RECORD_EVENT,
}));

import { buildRateLimiter, RateLimiterConfigurationError } from "../_rate-limiter";

describe("buildRateLimiter (keys)", () => {
  beforeEach(() => {
    GET_ENV_VAR.mockReset();
    GET_ENV_VAR_FALLBACK.mockReset();
    GET_REDIS.mockReset();
    RECORD_EVENT.mockReset();
  });

  it("returns undefined when Redis is missing outside production", () => {
    GET_ENV_VAR.mockReturnValue("test");
    GET_REDIS.mockReturnValue(undefined);

    expect(buildRateLimiter()).toBeUndefined();
    expect(RECORD_EVENT).not.toHaveBeenCalled();
  });

  it("throws in production when Redis is missing", () => {
    GET_ENV_VAR.mockReturnValue("production");
    GET_REDIS.mockReturnValue(undefined);
    GET_ENV_VAR_FALLBACK.mockReturnValue(undefined);

    expect(() => buildRateLimiter()).toThrow(RateLimiterConfigurationError);
    expect(RECORD_EVENT).toHaveBeenCalledWith(
      "api.keys.rate_limit_config_error",
      expect.objectContaining({
        attributes: expect.objectContaining({
          hasToken: false,
          hasUrl: false,
          message: expect.stringContaining("UPSTASH_REDIS_REST_URL"),
        }),
        level: "error",
      })
    );
  });

  it("returns a Ratelimit instance when Redis is available", () => {
    GET_ENV_VAR.mockReturnValue("production");
    GET_REDIS.mockReturnValue({});

    const limiter = buildRateLimiter();

    expect(limiter).toBeDefined();
    expect(limiter).toBeInstanceOf(Ratelimit);
    expect(RECORD_EVENT).not.toHaveBeenCalled();
  });
});
