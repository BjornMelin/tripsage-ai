/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const warnRedisUnavailableMock = vi.fn();

// Mock redis client and factories
const existsMock = vi.fn(async (_key: string) => 0);
type RedisClient = { exists: typeof existsMock };
let redisClient: RedisClient | undefined = { exists: existsMock };
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
    redisClient = { exists: existsMock };
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

    it("returns true and logs when redis unavailable with failOpen=false (fail-closed)", async () => {
      redisClient = undefined;

      const { hasKey } = await import("../redis");

      const result = await hasKey("missing", { failOpen: false });

      expect(result).toBe(true);
      expect(warnRedisUnavailableMock).toHaveBeenCalled();
    });
  });
});
