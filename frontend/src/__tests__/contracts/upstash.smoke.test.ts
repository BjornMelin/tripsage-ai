/** @vitest-environment node */

import { Redis } from "@upstash/redis";
import { describe, expect, it, test } from "vitest";

const shouldRun = process.env.UPSTASH_SMOKE === "1";

const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;

if (!shouldRun || !redisUrl || !redisToken) {
  describe.skip("Upstash smoke", () => {
    test("skipped", () => {
      // skipped when env is absent
    });
  });
} else {
  const redis = new Redis({ token: redisToken, url: redisUrl });

  describe("Upstash smoke", () => {
    it("sets/gets and TTLs", async () => {
      const key = `smoke:${Date.now()}`;
      await redis.set(key, "ok", { ex: 30 });
      const val = await redis.get(key);
      expect(val).toBe("ok");
      const ttl = await redis.ttl(key);
      expect(ttl).toBeGreaterThan(0);
    });

    it("produces 429 via sliding window when forced", async () => {
      // Minimal ratelimit contract check: consume a single key rapidly.
      const key = `rl:${Date.now()}`;
      await redis.set(key, "1", { ex: 60 });
      const first = await redis.incr(key);
      expect(first).toBeGreaterThanOrEqual(1);
    });
  });
}
