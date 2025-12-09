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
  const qstashUrl = process.env.UPSTASH_QSTASH_URL;
  const qstashToken = process.env.UPSTASH_QSTASH_TOKEN;

  const haveRedis = !!redisUrl && !!redisToken;
  const haveQstash = !!qstashUrl && !!qstashToken;

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
      const qstashUrl = required("UPSTASH_QSTASH_URL");
      const qstashToken = required("UPSTASH_QSTASH_TOKEN");

      const res = await fetch(qstashUrl, {
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
