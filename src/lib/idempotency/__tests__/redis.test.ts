/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const warnRedisUnavailableMock = vi.fn();

// Mock redis client and factories
const existsMock = vi.fn(async (_key: string) => 0);
const setMock = vi.fn(async () => "OK");
const delMock = vi.fn(async () => 1);
type RedisClient = {
  exists: typeof existsMock;
  set: typeof setMock;
  del: typeof delMock;
};
let redisClient: RedisClient | undefined = {
  del: delMock,
  exists: existsMock,
  set: setMock,
};
const getRedisMock = vi.fn(() => redisClient);

vi.mock("@/lib/redis", () => ({
  getRedis: () => getRedisMock(),
}));

vi.mock("@/lib/telemetry/redis", () => ({
  warnRedisUnavailable: (...args: unknown[]) => warnRedisUnavailableMock(...args),
}));

describe("idempotency redis helpers", () => {
  beforeEach(() => {
    existsMock.mockReset();
    setMock.mockReset();
    delMock.mockReset();
    redisClient = { del: delMock, exists: existsMock, set: setMock };
    getRedisMock.mockReset();
    warnRedisUnavailableMock.mockReset();
  });

  describe("hasKey", () => {
    it("returns true when key exists", async () => {
      existsMock.mockResolvedValueOnce(1);

      const { hasKey } = await import("../redis");

      const result = await hasKey("test");

      expect(result).toBe(true);
      expect(existsMock).toHaveBeenCalledWith("idemp:test");
    });

    it("returns false and logs when redis unavailable with failOpen (default)", async () => {
      redisClient = undefined;

      const { hasKey } = await import("../redis");

      const result = await hasKey("missing");

      expect(result).toBe(false);
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
    });

    it("returns true (treat as duplicate/already processed) and logs when redis unavailable with failOpen=false (fail-closed)", async () => {
      redisClient = undefined;

      const { hasKey } = await import("../redis");

      const result = await hasKey("missing", { failOpen: false });

      expect(result).toBe(true);
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
    });
  });

  describe("tryReserveKey", () => {
    it("reserves with NX and EX using idemp prefix and returns true on OK", async () => {
      setMock.mockResolvedValueOnce("OK");
      const { tryReserveKey } = await import("../redis");

      const result = await tryReserveKey("abc", 123);

      expect(result).toBe(true);
      expect(setMock).toHaveBeenCalledWith("idemp:abc", "1", {
        ex: 123,
        nx: true,
      });
    });

    it("returns false when set returns null", async () => {
      setMock.mockResolvedValueOnce(null as never);
      const { tryReserveKey } = await import("../redis");

      const result = await tryReserveKey("abc", 60);

      expect(result).toBe(false);
    });

    it("throws when redis unavailable and failOpen=false", async () => {
      redisClient = undefined;
      const { tryReserveKey } = await import("../redis");

      await expect(() =>
        tryReserveKey("abc", { failOpen: false, ttlSeconds: 10 })
      ).rejects.toThrow("Idempotency service unavailable");
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
    });

    it("returns true when redis unavailable and failOpen=true", async () => {
      redisClient = undefined;
      const { tryReserveKey } = await import("../redis");

      const result = await tryReserveKey("abc", { failOpen: true, ttlSeconds: 10 });

      expect(result).toBe(true);
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
    });

    it("passes ttlSeconds from options", async () => {
      setMock.mockResolvedValueOnce("OK");
      const { tryReserveKey } = await import("../redis");

      await tryReserveKey("abc", { ttlSeconds: 42 });

      expect(setMock).toHaveBeenCalledWith(
        "idemp:abc",
        "1",
        expect.objectContaining({ ex: 42 })
      );
    });
  });

  describe("releaseKey", () => {
    it("deletes prefixed key and returns true when deletion succeeds", async () => {
      delMock.mockResolvedValueOnce(1);
      const { releaseKey } = await import("../redis");

      const result = await releaseKey("abc");

      expect(result).toBe(true);
      expect(delMock).toHaveBeenCalledWith("idemp:abc");
    });

    it("returns false when redis unavailable and logs (failOpen default)", async () => {
      redisClient = undefined;
      const { releaseKey } = await import("../redis");

      const result = await releaseKey("abc");

      expect(result).toBe(false);
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
    });

    it("throws when redis unavailable and failOpen=false", async () => {
      redisClient = undefined;
      const { releaseKey } = await import("../redis");

      await expect(releaseKey("abc", { failOpen: false })).rejects.toThrow(
        "Idempotency service unavailable"
      );
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
    });

    it("returns false when del returns 0", async () => {
      delMock.mockResolvedValueOnce(0);
      const { releaseKey } = await import("../redis");

      const result = await releaseKey("abc");

      expect(result).toBe(false);
    });
  });
});
