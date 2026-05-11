/** @vitest-environment node */

import { describe, expect, it } from "vitest";

const required = (key: string) => {
  const val = process.env[key];
  if (!val) {
    throw new Error(`Missing env ${key}`);
  }
  return val;
};

describe("Upstash live smoke", () => {
  const enabled = process.env.UPSTASH_SMOKE === "1";

  const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
  const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;
  const qstashTargetUrl = process.env.UPSTASH_QSTASH_SMOKE_TARGET_URL;
  const qstashToken = process.env.QSTASH_TOKEN;

  const haveRedis = !!redisUrl && !!redisToken;
  const haveQstash = !!qstashTargetUrl && !!qstashToken;

  it.skipIf(!enabled || !haveRedis)(
    "hits Redis set/get and ratelimit",
    async () => {
      const redisUrl = required("UPSTASH_REDIS_REST_URL");
      const redisToken = required("UPSTASH_REDIS_REST_TOKEN");

      const setRes = await fetch(`${redisUrl}/set/key/smoke`, {
        headers: { authorization: `Bearer ${redisToken}` },
        method: "POST",
      });
      expect(setRes.ok).toBe(true);

      const getRes = await fetch(`${redisUrl}/get/key`, {
        headers: { authorization: `Bearer ${redisToken}` },
        method: "GET",
      });
      expect(getRes.ok).toBe(true);
      const body = await getRes.json();
      expect(body.result).toBeDefined();
    },
    20000
  );

  it.skipIf(!enabled || !haveQstash)(
    "publishes QStash message",
    async () => {
      const qstashTargetUrl = required("UPSTASH_QSTASH_SMOKE_TARGET_URL");
      const qstashToken = required("QSTASH_TOKEN");
      const publishUrl = `https://qstash.upstash.io/v2/publish/${encodeURIComponent(
        qstashTargetUrl
      )}`;

      const res = await fetch(publishUrl, {
        body: JSON.stringify({ hello: "world" }),
        headers: {
          Authorization: `Bearer ${qstashToken}`,
          "Content-Type": "application/json",
        },
        method: "POST",
      });
      expect(res.ok).toBe(true);
    },
    20000
  );
});
