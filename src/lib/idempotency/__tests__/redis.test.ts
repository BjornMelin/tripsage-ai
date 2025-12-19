/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const warnRedisUnavailableMock = vi.fn();
const emitOperationalAlertOncePerWindowMock = vi.fn();

// Mock redis client and factories
const existsMock = vi.fn(async () => 0);
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

vi.mock("@/lib/telemetry/degraded-mode", () => ({
  emitOperationalAlertOncePerWindow: (...args: unknown[]) =>
    emitOperationalAlertOncePerWindowMock(...args),
}));

describe("idempotency redis helpers", () => {
  beforeEach(() => {
    existsMock.mockReset();
    setMock.mockReset();
    delMock.mockReset();
    redisClient = { del: delMock, exists: existsMock, set: setMock };
    getRedisMock.mockReset();
    warnRedisUnavailableMock.mockReset();
    emitOperationalAlertOncePerWindowMock.mockReset();
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
      // Note: no operational alert when Redis is unavailable, only on Redis errors
      expect(emitOperationalAlertOncePerWindowMock).not.toHaveBeenCalled();
    });

    it("returns false and emits degraded alert when redis throws error with failOpen=true", async () => {
      existsMock.mockRejectedValueOnce(new Error("Timeout"));

      const { hasKey } = await import("../redis");

      const result = await hasKey("test");

      expect(result).toBe(false);
      expect(warnRedisUnavailableMock).toHaveBeenCalledWith(
        "idempotency.keys",
        expect.objectContaining({ errorMessage: "Timeout" })
      );
      expect(emitOperationalAlertOncePerWindowMock).toHaveBeenCalledWith(
        expect.objectContaining({
          attributes: expect.objectContaining({
            degradedMode: "fail_open",
            errorMessage: "Timeout",
            reason: "redis_error",
          }),
          event: "idempotency.degraded",
        })
      );
    });

    it("returns true and emits degraded alert when redis throws error with failOpen=false (fail-closed)", async () => {
      existsMock.mockRejectedValueOnce(new Error("Timeout"));

      const { hasKey } = await import("../redis");

      const result = await hasKey("test", { failOpen: false });

      expect(result).toBe(true);
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
      expect(emitOperationalAlertOncePerWindowMock).toHaveBeenCalledWith(
        expect.objectContaining({
          attributes: expect.objectContaining({
            degradedMode: "fail_closed",
            errorMessage: "Timeout",
            reason: "redis_error",
          }),
          event: "idempotency.degraded",
        })
      );
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

    it("returns true when redis unavailable and failOpen=true and emits degraded alert", async () => {
      redisClient = undefined;
      const { tryReserveKey } = await import("../redis");

      const result = await tryReserveKey("abc", { failOpen: true, ttlSeconds: 10 });

      expect(result).toBe(true);
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
      expect(emitOperationalAlertOncePerWindowMock).toHaveBeenCalledWith(
        expect.objectContaining({
          attributes: expect.objectContaining({
            degradedMode: "fail_open",
            reason: "redis_unavailable",
          }),
          event: "idempotency.degraded",
        })
      );
    });

    it("returns true and emits degraded alert when redis throws error with failOpen=true", async () => {
      setMock.mockRejectedValueOnce(new Error("Connection refused"));
      const { tryReserveKey } = await import("../redis");

      const result = await tryReserveKey("abc", { failOpen: true, ttlSeconds: 10 });

      expect(result).toBe(true);
      expect(warnRedisUnavailableMock).toHaveBeenCalledWith(
        "idempotency.keys",
        expect.objectContaining({ errorMessage: "Connection refused" })
      );
      expect(emitOperationalAlertOncePerWindowMock).toHaveBeenCalledWith(
        expect.objectContaining({
          attributes: expect.objectContaining({
            degradedMode: "fail_open",
            errorMessage: "Connection refused",
            reason: "redis_error",
          }),
          event: "idempotency.degraded",
        })
      );
    });

    it("throws and does not emit alert when redis throws error with failOpen=false", async () => {
      setMock.mockRejectedValueOnce(new Error("Connection refused"));
      const { tryReserveKey } = await import("../redis");

      await expect(
        tryReserveKey("abc", { failOpen: false, ttlSeconds: 10 })
      ).rejects.toThrow("Idempotency service unavailable");
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
      expect(emitOperationalAlertOncePerWindowMock).not.toHaveBeenCalled();
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

    it("returns false and emits degraded alert when redis throws error with failOpen=true", async () => {
      delMock.mockRejectedValueOnce(new Error("Network error"));
      const { releaseKey } = await import("../redis");

      const result = await releaseKey("abc");

      expect(result).toBe(false);
      expect(warnRedisUnavailableMock).toHaveBeenCalledWith(
        "idempotency.keys",
        expect.objectContaining({ errorMessage: "Network error" })
      );
      expect(emitOperationalAlertOncePerWindowMock).toHaveBeenCalledWith(
        expect.objectContaining({
          attributes: expect.objectContaining({
            degradedMode: "fail_open",
            errorMessage: "Network error",
            reason: "redis_error",
          }),
          event: "idempotency.degraded",
        })
      );
    });

    it("throws and does not emit alert when redis throws error with failOpen=false", async () => {
      delMock.mockRejectedValueOnce(new Error("Network error"));
      const { releaseKey } = await import("../redis");

      await expect(releaseKey("abc", { failOpen: false })).rejects.toThrow(
        "Idempotency service unavailable"
      );
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
      expect(emitOperationalAlertOncePerWindowMock).not.toHaveBeenCalled();
    });
  });
});
