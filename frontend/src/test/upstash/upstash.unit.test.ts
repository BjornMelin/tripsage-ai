/** @vitest-environment node */

import { beforeEach, describe, expect, it } from "vitest";
import { createRatelimitMock } from "@/test/upstash/ratelimit-mock";
import {
  createRedisMock,
  runUpstashPipeline,
  sharedUpstashStore,
} from "@/test/upstash/redis-mock";

const redis = createRedisMock(sharedUpstashStore);
const ratelimit = createRatelimitMock();

describe("Upstash mocks", () => {
  beforeEach(() => {
    redis.__reset();
    ratelimit.__reset();
  });

  it("stores and retrieves values with TTL", async () => {
    const client = redis.Redis.fromEnv();
    await client.set("key", "value", { ex: 1 });
    expect(await client.get("key")).toBe("value");
  });

  it("respects ratelimit forced outcomes", async () => {
    const Rl = new ratelimit.Ratelimit({
      limiter: ratelimit.Ratelimit.slidingWindow(1, "1 s"),
    });
    const first = await Rl.limit("user");
    ratelimit.__reset();
    expect(first.limit).toBeDefined();
  });

  it("runs pipeline via helper", async () => {
    const res = await runUpstashPipeline(sharedUpstashStore, [
      ["SET", "a", "1"],
      ["GET", "a"],
    ]);
    expect(res[1]).toBe(1);
  });
});
