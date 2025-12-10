/** @vitest-environment node */

import { beforeEach, describe, expect, it } from "vitest";
import { createRedisMock, sharedUpstashStore } from "@/test/upstash/redis-mock";

const redisMock = createRedisMock(sharedUpstashStore);

describe("Redis mock for idempotency", () => {
  beforeEach(() => {
    redisMock.__reset();
  });

  describe("basic operations", () => {
    it("stores and retrieves values", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:test-key", "test-value", { ex: 300 });
      const value = await client.get("idemp:test-key");

      expect(value).toBe("test-value");
    });

    it("returns null for missing keys", async () => {
      const client = redisMock.Redis.fromEnv();

      const value = await client.get("idemp:nonexistent");

      expect(value).toBeNull();
    });

    it("stores and retrieves JSON values", async () => {
      const client = redisMock.Redis.fromEnv();
      const data = { status: "processed", userId: "123" };

      await client.set("idemp:json-key", data);
      const value = await client.get("idemp:json-key");

      expect(value).toEqual(data);
    });
  });

  describe("TTL handling", () => {
    it("respects TTL for keys (ex option)", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:ttl-test", "1", { ex: 60 });
      const ttl = await client.ttl("idemp:ttl-test");

      expect(ttl).toBeGreaterThanOrEqual(0);
      expect(ttl).toBeLessThanOrEqual(60);
    });

    it("respects TTL for keys (px option)", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:ttl-px-test", "1", { px: 5000 });
      const ttl = await client.ttl("idemp:ttl-px-test");

      // TTL returns seconds, so 5000ms = ~5s
      expect(ttl).toBeGreaterThanOrEqual(0);
      expect(ttl).toBeLessThanOrEqual(5);
    });

    it("returns -1 for keys without TTL", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:no-ttl", "1");
      const ttl = await client.ttl("idemp:no-ttl");

      expect(ttl).toBe(-1);
    });

    it("returns -2 for non-existent keys", async () => {
      const client = redisMock.Redis.fromEnv();

      const ttl = await client.ttl("idemp:nonexistent");

      expect(ttl).toBe(-2);
    });

    it("allows setting TTL on existing key via expire", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:expire-test", "1");
      const result = await client.expire("idemp:expire-test", 30);
      const ttl = await client.ttl("idemp:expire-test");

      expect(result).toBe(1);
      expect(ttl).toBeGreaterThanOrEqual(0);
      expect(ttl).toBeLessThanOrEqual(30);
    });
  });

  describe("key deletion", () => {
    it("deletes single key", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:delete-test", "1");
      const deleted = await client.del("idemp:delete-test");
      const value = await client.get("idemp:delete-test");

      expect(deleted).toBe(1);
      expect(value).toBeNull();
    });

    it("deletes multiple keys", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:del-a", "1");
      await client.set("idemp:del-b", "2");
      await client.set("idemp:del-c", "3");
      const deleted = await client.del("idemp:del-a", "idemp:del-b", "idemp:del-c");

      expect(deleted).toBe(3);
    });

    it("returns 0 for deleting non-existent key", async () => {
      const client = redisMock.Redis.fromEnv();

      const deleted = await client.del("idemp:nonexistent");

      expect(deleted).toBe(0);
    });
  });

  describe("counter operations", () => {
    it("increments counters from zero", async () => {
      const client = redisMock.Redis.fromEnv();

      const v1 = await client.incr("counter:test");
      const v2 = await client.incr("counter:test");

      expect(v1).toBe(1);
      expect(v2).toBe(2);
    });

    it("increments existing numeric values", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("counter:existing", "10");
      const v1 = await client.incr("counter:existing");

      expect(v1).toBe(11);
    });
  });

  describe("mget operations", () => {
    it("retrieves multiple keys at once", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("mget:a", "value-a");
      await client.set("mget:b", "value-b");

      const [a, b, c] = await client.mget("mget:a", "mget:b", "mget:nonexistent");

      expect(a).toBe("value-a");
      expect(b).toBe("value-b");
      expect(c).toBeNull();
    });

    it("returns all nulls for non-existent keys", async () => {
      const client = redisMock.Redis.fromEnv();

      const results = await client.mget("missing:1", "missing:2");

      expect(results).toEqual([null, null]);
    });

    it("deserializes JSON values", async () => {
      const client = redisMock.Redis.fromEnv();
      const objA = { id: 1, name: "test" };
      const objB = { id: 2, name: "other" };

      await client.set("mget:json-a", objA);
      await client.set("mget:json-b", objB);

      const [a, b] = await client.mget("mget:json-a", "mget:json-b");

      expect(a).toEqual(objA);
      expect(b).toEqual(objB);
    });
  });

  describe("exists operations", () => {
    it("counts existing keys", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("exists:a", "1");
      await client.set("exists:b", "2");

      const count = await client.exists("exists:a", "exists:b", "exists:missing");

      expect(count).toBe(2);
    });

    it("returns 0 for no existing keys", async () => {
      const client = redisMock.Redis.fromEnv();

      const count = await client.exists("missing:1", "missing:2");

      expect(count).toBe(0);
    });

    it("returns count for all existing keys", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("all:a", "1");
      await client.set("all:b", "2");
      await client.set("all:c", "3");

      const count = await client.exists("all:a", "all:b", "all:c");

      expect(count).toBe(3);
    });

    it("does not count expired keys", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("expire:exists", "1", { px: 1 });
      await new Promise((r) => setTimeout(r, 10));

      const count = await client.exists("expire:exists");

      expect(count).toBe(0);
    });
  });

  describe("mset operations", () => {
    it("sets multiple keys with object syntax", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.mset({
        "idemp:a": "value-a",
        "idemp:b": "value-b",
        "idemp:c": "value-c",
      });

      expect(await client.get("idemp:a")).toBe("value-a");
      expect(await client.get("idemp:b")).toBe("value-b");
      expect(await client.get("idemp:c")).toBe("value-c");
    });

    it("sets multiple keys with array syntax", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.mset([
        ["idemp:x", "value-x"],
        ["idemp:y", "value-y"],
      ]);

      expect(await client.get("idemp:x")).toBe("value-x");
      expect(await client.get("idemp:y")).toBe("value-y");
    });
  });

  describe("reset behavior", () => {
    it("clears all stored data", async () => {
      const client = redisMock.Redis.fromEnv();

      await client.set("idemp:reset-test", "test-value");
      expect(await client.get("idemp:reset-test")).toBe("test-value");

      redisMock.__reset();

      expect(await client.get("idemp:reset-test")).toBeNull();
    });
  });
});
