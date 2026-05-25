/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

// Hoisted mocks per testing.md Pattern A
const mockRedisGet = vi.hoisted(() => vi.fn());
const mockRedisSet = vi.hoisted(() => vi.fn());
const mockRedisDel = vi.hoisted(() => vi.fn());

type MockRedisClient = {
  del: ReturnType<typeof vi.fn>;
  get: ReturnType<typeof vi.fn>;
  set: ReturnType<typeof vi.fn>;
} | null;

const mockGetRedis = vi.hoisted(() => {
  const mock = vi.fn<() => MockRedisClient>();
  mock.mockReturnValue({
    del: mockRedisDel,
    get: mockRedisGet,
    set: mockRedisSet,
  });
  return mock;
});

vi.mock("@/lib/redis", () => ({
  getRedis: mockGetRedis,
}));

import {
  deleteCachedJson,
  deleteCachedJsonMany,
  getCachedJson,
  getCachedJsonSafe,
  invalidateUserCache,
  setCachedJson,
} from "../upstash";

describe("getCachedJson", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRedisGet.mockReset();
    mockRedisSet.mockReset();
    mockRedisDel.mockReset();
  });

  it("returns null when Redis is not available", async () => {
    mockGetRedis.mockReturnValueOnce(null);

    const result = await getCachedJson("test-key");

    expect(result).toBeNull();
  });

  it("returns null when key does not exist", async () => {
    mockRedisGet.mockResolvedValue(null);

    const result = await getCachedJson("missing-key");

    expect(result).toBeNull();
    expect(mockRedisGet).toHaveBeenCalledWith("missing-key");
  });

  it("returns SDK-deserialized cache data", async () => {
    const testData = { name: "test", value: 123 };
    mockRedisGet.mockResolvedValue(testData);

    const result = await getCachedJson<typeof testData>("valid-key");

    expect(result).toEqual(testData);
  });

  it("returns string cache values from SDK deserialization", async () => {
    mockRedisGet.mockResolvedValue("just a string");

    const result = await getCachedJson<string>("string-key");

    expect(result).toBe("just a string");
  });

  it("returns null when Redis throws", async () => {
    mockRedisGet.mockRejectedValueOnce(new Error("boom"));

    const result = await getCachedJson("throwing-key");

    expect(result).toBeNull();
  });

  it("handles complex nested objects", async () => {
    const complexData = {
      array: [1, 2, 3],
      date: "2025-01-01T00:00:00Z",
      nested: { deep: { value: "test" } },
    };
    mockRedisGet.mockResolvedValue(complexData);

    const result = await getCachedJson<typeof complexData>("complex-key");

    expect(result).toEqual(complexData);
  });
});

describe("getCachedJsonSafe", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRedisGet.mockReset();
  });

  it("returns unavailable status when Redis is not available", async () => {
    mockGetRedis.mockReturnValueOnce(null);

    const result = await getCachedJsonSafe("test-key");

    expect(result).toEqual({ status: "unavailable" });
  });

  it("returns miss status when key does not exist", async () => {
    mockRedisGet.mockResolvedValue(null);

    const result = await getCachedJsonSafe("missing-key");

    expect(result).toEqual({ status: "miss" });
  });

  it("returns hit status with data for valid JSON", async () => {
    const testData = { id: 1, name: "test" };
    mockRedisGet.mockResolvedValue(testData);

    const result = await getCachedJsonSafe<typeof testData>("valid-key");

    expect(result).toEqual({ data: testData, status: "hit" });
  });

  it("returns hit status for string values when no schema is provided", async () => {
    mockRedisGet.mockResolvedValue("invalid json {{");

    const result = await getCachedJsonSafe<string>("string-key");

    expect(result).toEqual({ data: "invalid json {{", status: "hit" });
  });

  it("returns unavailable status when Redis throws", async () => {
    mockRedisGet.mockRejectedValueOnce(new Error("boom"));

    const result = await getCachedJsonSafe("throwing-key");

    expect(result).toEqual({ status: "unavailable" });
  });

  it("validates data against Zod schema when provided", async () => {
    const schema = z.strictObject({
      id: z.number().int(),
      name: z.string(),
    });
    const validData = { id: 1, name: "test" };
    mockRedisGet.mockResolvedValue(validData);

    const result = await getCachedJsonSafe("schema-key", schema);

    expect(result).toEqual({ data: validData, status: "hit" });
  });

  it("returns invalid status when schema validation fails", async () => {
    const schema = z.strictObject({
      id: z.number().int(),
      name: z.string(),
    });
    const invalidData = { id: "not-a-number", name: 123 };
    mockRedisGet.mockResolvedValue(invalidData);

    const result = await getCachedJsonSafe("invalid-schema-key", schema);

    expect(result.status).toBe("invalid");
    expect(result).toHaveProperty("raw");
  });
});

describe("setCachedJson", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRedisSet.mockReset();
    mockRedisSet.mockResolvedValue("OK");
  });

  it("does nothing when Redis is not available", async () => {
    mockGetRedis.mockReturnValueOnce(null);

    await setCachedJson("test-key", { data: "test" });

    expect(mockRedisSet).not.toHaveBeenCalled();
  });

  it("does not throw when Redis throws", async () => {
    mockRedisSet.mockRejectedValueOnce(new Error("boom"));

    await expect(
      setCachedJson("throwing-key", { data: "test" })
    ).resolves.toBeUndefined();
  });

  it("sets values directly without TTL", async () => {
    const testData = { name: "test", value: 42 };

    await setCachedJson("no-ttl-key", testData);

    expect(mockRedisSet).toHaveBeenCalledWith("no-ttl-key", testData);
  });

  it("sets value with TTL when ttlSeconds is positive", async () => {
    const testData = { cached: true };

    await setCachedJson("ttl-key", testData, 300);

    expect(mockRedisSet).toHaveBeenCalledWith("ttl-key", testData, {
      ex: 300,
    });
  });

  it("ignores TTL when ttlSeconds is zero", async () => {
    const testData = { value: "test" };

    await setCachedJson("zero-ttl-key", testData, 0);

    expect(mockRedisSet).toHaveBeenCalledWith("zero-ttl-key", testData);
  });

  it("ignores TTL when ttlSeconds is negative", async () => {
    const testData = { value: "test" };

    await setCachedJson("negative-ttl-key", testData, -100);

    expect(mockRedisSet).toHaveBeenCalledWith("negative-ttl-key", testData);
  });

  it("handles arrays", async () => {
    const arrayData = [1, 2, 3, "test"];

    await setCachedJson("array-key", arrayData);

    expect(mockRedisSet).toHaveBeenCalledWith("array-key", arrayData);
  });

  it("handles primitive values", async () => {
    await setCachedJson("string-key", "just a string");

    expect(mockRedisSet).toHaveBeenCalledWith("string-key", "just a string");
  });
});

describe("deleteCachedJson", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRedisDel.mockReset();
    mockRedisDel.mockResolvedValue(1);
  });

  it("does nothing when Redis is not available", async () => {
    mockGetRedis.mockReturnValueOnce(null);

    await deleteCachedJson("test-key");

    expect(mockRedisDel).not.toHaveBeenCalled();
  });

  it("does not throw when Redis throws", async () => {
    mockRedisDel.mockRejectedValueOnce(new Error("boom"));

    await expect(deleteCachedJson("throwing-key")).resolves.toBeUndefined();
  });

  it("deletes the specified key", async () => {
    await deleteCachedJson("delete-me");

    expect(mockRedisDel).toHaveBeenCalledWith("delete-me");
  });
});

describe("deleteCachedJsonMany", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRedisDel.mockReset();
    mockRedisDel.mockResolvedValue(3);
  });

  it("returns 0 when Redis is not available", async () => {
    mockGetRedis.mockReturnValueOnce(null);

    const result = await deleteCachedJsonMany(["key1", "key2"]);

    expect(result).toBe(0);
    expect(mockRedisDel).not.toHaveBeenCalled();
  });

  it("returns 0 when keys array is empty", async () => {
    const result = await deleteCachedJsonMany([]);

    expect(result).toBe(0);
    expect(mockRedisDel).not.toHaveBeenCalled();
  });

  it("returns 0 when Redis throws", async () => {
    mockRedisDel.mockRejectedValueOnce(new Error("boom"));

    const result = await deleteCachedJsonMany(["key1", "key2"]);

    expect(result).toBe(0);
  });

  it("deletes multiple keys and returns count", async () => {
    const keys = ["key1", "key2", "key3"];

    const result = await deleteCachedJsonMany(keys);

    expect(result).toBe(3);
    expect(mockRedisDel).toHaveBeenCalledWith("key1", "key2", "key3");
  });
});

describe("invalidateUserCache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRedisDel.mockReset();
    mockRedisDel.mockResolvedValue(2);
  });

  it("constructs correct keys and deletes them", async () => {
    await invalidateUserCache("user-123", ["trips:list", "trips:suggestions"]);

    expect(mockRedisDel).toHaveBeenCalledWith(
      "trips:list:user-123:all",
      "trips:suggestions:user-123:all"
    );
  });

  it("handles single cache type", async () => {
    await invalidateUserCache("user-456", ["profile"]);

    expect(mockRedisDel).toHaveBeenCalledWith("profile:user-456:all");
  });

  it("does nothing when cacheTypes is empty", async () => {
    await invalidateUserCache("user-789", []);

    expect(mockRedisDel).not.toHaveBeenCalled();
  });
});
