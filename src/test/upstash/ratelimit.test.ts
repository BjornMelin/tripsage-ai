/** @vitest-environment node */

import { beforeEach, describe, expect, it } from "vitest";
import { createRatelimitMock } from "@/test/upstash/ratelimit-mock";

const ratelimit = createRatelimitMock();

describe("RatelimitMock", () => {
  beforeEach(() => {
    ratelimit.__reset();
  });

  describe("sliding window behavior", () => {
    it("allows requests within limit", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(3, "1 m"),
      });

      const r1 = await limiter.limit("user-1");
      const r2 = await limiter.limit("user-1");
      const r3 = await limiter.limit("user-1");

      expect(r1.success).toBe(true);
      expect(r1.remaining).toBe(2);
      expect(r2.success).toBe(true);
      expect(r2.remaining).toBe(1);
      expect(r3.success).toBe(true);
      expect(r3.remaining).toBe(0);
    });

    it("rejects requests exceeding limit", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(2, "1 m"),
      });

      await limiter.limit("user-1");
      await limiter.limit("user-1");
      const r3 = await limiter.limit("user-1");

      expect(r3.success).toBe(false);
      expect(r3.remaining).toBe(0);
      expect(r3.retryAfter).toBeGreaterThan(0);
    });

    it("isolates identifiers", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(1, "1 m"),
      });

      const r1 = await limiter.limit("user-1");
      const r2 = await limiter.limit("user-2");

      expect(r1.success).toBe(true);
      expect(r2.success).toBe(true);
    });

    it("returns correct limit value", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(5, "1 m"),
      });

      const result = await limiter.limit("user-1");

      expect(result.limit).toBe(5);
    });

    it("returns reset timestamp in the future", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(3, "1 m"),
      });

      const result = await limiter.limit("user-1");

      expect(result.reset).toBeGreaterThan(Date.now());
    });
  });

  describe("window time parsing", () => {
    it("parses seconds", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(1, "30 s"),
      });

      const r1 = await limiter.limit("user-1");
      expect(r1.reset).toBeLessThanOrEqual(Date.now() + 31_000);
    });

    it("parses minutes", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(1, "2 m"),
      });

      const r1 = await limiter.limit("user-1");
      expect(r1.reset).toBeLessThanOrEqual(Date.now() + 121_000);
    });

    it("parses hours", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(1, "1 h"),
      });

      const r1 = await limiter.limit("user-1");
      expect(r1.reset).toBeLessThanOrEqual(Date.now() + 3_601_000);
    });
  });

  describe("fixed window behavior", () => {
    it("allows requests within limit", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.fixedWindow(3, "1 m"),
      });

      const r1 = await limiter.limit("user-1");
      const r2 = await limiter.limit("user-1");
      const r3 = await limiter.limit("user-1");

      expect(r1.success).toBe(true);
      expect(r1.remaining).toBe(2);
      expect(r2.success).toBe(true);
      expect(r2.remaining).toBe(1);
      expect(r3.success).toBe(true);
      expect(r3.remaining).toBe(0);
    });

    it("rejects requests exceeding limit", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.fixedWindow(2, "1 m"),
      });

      await limiter.limit("user-1");
      await limiter.limit("user-1");
      const r3 = await limiter.limit("user-1");

      expect(r3.success).toBe(false);
      expect(r3.remaining).toBe(0);
      expect(r3.retryAfter).toBeGreaterThan(0);
    });

    it("isolates identifiers", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.fixedWindow(1, "1 m"),
      });

      const r1 = await limiter.limit("user-1");
      const r2 = await limiter.limit("user-2");

      expect(r1.success).toBe(true);
      expect(r2.success).toBe(true);
    });

    it("returns correct limit value", async () => {
      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.fixedWindow(5, "1 m"),
      });

      const result = await limiter.limit("user-1");

      expect(result.limit).toBe(5);
    });
  });

  describe("forced outcomes", () => {
    it("can force success=false globally", async () => {
      ratelimit.__force({ success: false });

      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(100, "1 m"),
      });

      const result = await limiter.limit("user-1");

      expect(result.success).toBe(false);
    });

    it("can force custom remaining value", async () => {
      ratelimit.__force({ remaining: 42, success: true });

      const limiter = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(100, "1 m"),
      });

      const result = await limiter.limit("user-1");

      expect(result.success).toBe(true);
      expect(result.remaining).toBe(42);
    });
  });

  describe("reset behavior", () => {
    it("clears all rate limit state", async () => {
      const limiter1 = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(1, "1 m"),
      });

      await limiter1.limit("user-1");
      const r1 = await limiter1.limit("user-1");
      expect(r1.success).toBe(false);

      ratelimit.__reset();

      // Create fresh limiter after reset to verify clean state
      const limiter2 = new ratelimit.Ratelimit({
        limiter: ratelimit.Ratelimit.slidingWindow(1, "1 m"),
      });
      const r2 = await limiter2.limit("user-1");
      expect(r2.success).toBe(true);
    });
  });
});
