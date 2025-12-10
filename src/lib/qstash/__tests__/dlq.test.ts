/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Hoisted mocks
const mockRedisLpush = vi.hoisted(() => vi.fn());
const mockRedisLtrim = vi.hoisted(() => vi.fn());
const mockRedisExpire = vi.hoisted(() => vi.fn());
const mockRedisLrange = vi.hoisted(() => vi.fn());
const mockRedisScan = vi.hoisted(() => vi.fn());
const mockRedisDel = vi.hoisted(() => vi.fn());
const mockRedisRpush = vi.hoisted(() => vi.fn());
const mockRedisLrem = vi.hoisted(() => vi.fn());
const mockRedisLlen = vi.hoisted(() => vi.fn());
const mockSecureUuid = vi.hoisted(() => vi.fn(() => "test-uuid-12345"));
const mockNowIso = vi.hoisted(() => vi.fn(() => "2025-12-10T12:00:00.000Z"));
const mockRecordTelemetryEvent = vi.hoisted(() => vi.fn());

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => ({
    del: mockRedisDel,
    expire: mockRedisExpire,
    llen: mockRedisLlen,
    lpush: mockRedisLpush,
    lrange: mockRedisLrange,
    lrem: mockRedisLrem,
    ltrim: mockRedisLtrim,
    rpush: mockRedisRpush,
    scan: mockRedisScan,
  })),
}));

// Mock security/random
vi.mock("@/lib/security/random", () => ({
  nowIso: () => mockNowIso(),
  secureUuid: () => mockSecureUuid(),
}));

// Mock telemetry
vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: (...args: unknown[]) => mockRecordTelemetryEvent(...args),
  withTelemetrySpan: async (
    _name: string,
    _opts: unknown,
    fn: (span: Record<string, unknown>) => unknown
  ) =>
    fn({
      addEvent: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
    }),
}));

describe("DLQ", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRedisLpush.mockResolvedValue(1);
    mockRedisLtrim.mockResolvedValue("OK");
    mockRedisExpire.mockResolvedValue(1);
    mockRedisLrange.mockResolvedValue([]);
    mockRedisScan.mockResolvedValue([0, []]);
    mockRedisDel.mockResolvedValue(1);
    mockRedisRpush.mockResolvedValue(1);
    mockRedisLrem.mockResolvedValue(1);
    mockRedisLlen.mockResolvedValue(0);
  });

  describe("pushToDLQ", () => {
    it("adds entry to Redis list with correct structure", async () => {
      const { pushToDLQ } = await import("../dlq");

      const entryId = await pushToDLQ(
        "notify-collaborators",
        { eventKey: "test-key", payload: { foo: "bar" } },
        new Error("Test error"),
        3
      );

      expect(entryId).toBe("test-uuid-12345");
      expect(mockRedisLpush).toHaveBeenCalledWith(
        "qstash-dlq:notify-collaborators",
        expect.stringContaining('"id":"test-uuid-12345"')
      );

      // Verify the structure of the pushed entry
      const pushedEntry = JSON.parse(mockRedisLpush.mock.calls[0][1]);
      expect(pushedEntry).toMatchObject({
        attempts: 3,
        error: "Test error",
        failedAt: "2025-12-10T12:00:00.000Z",
        id: "test-uuid-12345",
        jobType: "notify-collaborators",
        payload: { eventKey: "test-key", payload: { foo: "bar" } },
      });
      // M7: Error stack traces are now included
      expect(pushedEntry.errorStack).toContain("Error: Test error");
    });

    it("trims list to max entries", async () => {
      const { pushToDLQ } = await import("../dlq");

      await pushToDLQ("test-job", {}, "error", 1);

      expect(mockRedisLtrim).toHaveBeenCalledWith(
        "qstash-dlq:test-job",
        0,
        999 // DLQ_MAX_ENTRIES - 1
      );
    });

    it("sets TTL on the list", async () => {
      const { pushToDLQ } = await import("../dlq");

      await pushToDLQ("test-job", {}, "error", 1);

      expect(mockRedisExpire).toHaveBeenCalledWith(
        "qstash-dlq:test-job",
        604800 // 7 days in seconds
      );
    });

    it("handles string error messages", async () => {
      const { pushToDLQ } = await import("../dlq");

      await pushToDLQ("test-job", {}, "String error message", 1);

      const pushedEntry = JSON.parse(mockRedisLpush.mock.calls[0][1]);
      expect(pushedEntry.error).toBe("String error message");
    });

    it("returns null when Redis is unavailable", async () => {
      const { getRedis } = await import("@/lib/redis");
      vi.mocked(getRedis).mockReturnValueOnce(undefined);

      const { pushToDLQ } = await import("../dlq");
      const entryId = await pushToDLQ("test-job", {}, "error", 1);

      expect(entryId).toBeNull();
      expect(mockRedisLpush).not.toHaveBeenCalled();
    });
  });

  describe("listDLQEntries", () => {
    const validEntry = {
      attempts: 2,
      error: "Test error",
      failedAt: "2025-12-10T12:00:00.000Z",
      id: "entry-1",
      jobType: "notify-collaborators",
      payload: { test: true },
    };

    it("returns entries for specific job type", async () => {
      mockRedisLrange.mockResolvedValue([JSON.stringify(validEntry)]);

      const { listDLQEntries } = await import("../dlq");
      const entries = await listDLQEntries("notify-collaborators");

      expect(entries).toHaveLength(1);
      expect(entries[0]).toEqual(validEntry);
      expect(mockRedisLrange).toHaveBeenCalledWith(
        "qstash-dlq:notify-collaborators",
        0,
        99 // default limit - 1
      );
    });

    it("respects limit parameter", async () => {
      mockRedisLrange.mockResolvedValue([
        JSON.stringify(validEntry),
        JSON.stringify({ ...validEntry, id: "entry-2" }),
      ]);

      const { listDLQEntries } = await import("../dlq");
      await listDLQEntries("notify-collaborators", 1);

      // Only first entry returned due to limit
      expect(mockRedisLrange).toHaveBeenCalledWith(
        "qstash-dlq:notify-collaborators",
        0,
        0 // limit - 1
      );
    });

    it("scans all keys when no job type specified", async () => {
      mockRedisScan.mockResolvedValue([0, ["qstash-dlq:job1", "qstash-dlq:job2"]]);
      mockRedisLrange.mockResolvedValue([JSON.stringify(validEntry)]);

      const { listDLQEntries } = await import("../dlq");
      await listDLQEntries(undefined, 50);

      expect(mockRedisScan).toHaveBeenCalledWith(0, {
        count: 100,
        match: "qstash-dlq:*",
      });
      expect(mockRedisLrange).toHaveBeenCalledTimes(2);
    });

    it("returns empty array when Redis unavailable", async () => {
      const { getRedis } = await import("@/lib/redis");
      vi.mocked(getRedis).mockReturnValueOnce(undefined);

      const { listDLQEntries } = await import("../dlq");
      const entries = await listDLQEntries("test-job");

      expect(entries).toEqual([]);
    });

    it("skips invalid entries", async () => {
      mockRedisLrange.mockResolvedValue([
        JSON.stringify(validEntry),
        "invalid-json",
        JSON.stringify({ invalid: "schema" }),
      ]);

      const { listDLQEntries } = await import("../dlq");
      const entries = await listDLQEntries("notify-collaborators");

      // Only valid entry returned
      expect(entries).toHaveLength(1);
      expect(entries[0].id).toBe("entry-1");
    });
  });

  describe("removeDLQEntry", () => {
    const entry1 = {
      attempts: 1,
      error: "Error 1",
      failedAt: "2025-12-10T12:00:00.000Z",
      id: "entry-1",
      jobType: "test-job",
      payload: {},
    };
    const entry2 = {
      attempts: 2,
      error: "Error 2",
      failedAt: "2025-12-10T12:00:00.000Z",
      id: "entry-2",
      jobType: "test-job",
      payload: {},
    };

    it("removes entry by ID using atomic LREM", async () => {
      const entry1Str = JSON.stringify(entry1);
      mockRedisLrange.mockResolvedValue([entry1Str, JSON.stringify(entry2)]);
      mockRedisLrem.mockResolvedValue(1);

      const { removeDLQEntry } = await import("../dlq");
      const removed = await removeDLQEntry("test-job", "entry-1");

      expect(removed).toBe(true);
      // Should use atomic LREM instead of del/rpush (H1 fix)
      expect(mockRedisLrem).toHaveBeenCalledWith("qstash-dlq:test-job", 1, entry1Str);
      expect(mockRedisDel).not.toHaveBeenCalled();
      expect(mockRedisRpush).not.toHaveBeenCalled();
    });

    it("returns false when entry not found", async () => {
      mockRedisLrange.mockResolvedValue([JSON.stringify(entry1)]);

      const { removeDLQEntry } = await import("../dlq");
      const removed = await removeDLQEntry("test-job", "nonexistent");

      expect(removed).toBe(false);
      expect(mockRedisLrem).not.toHaveBeenCalled();
    });

    it("removes single entry successfully", async () => {
      const entry1Str = JSON.stringify(entry1);
      mockRedisLrange.mockResolvedValue([entry1Str]);
      mockRedisLrem.mockResolvedValue(1);

      const { removeDLQEntry } = await import("../dlq");
      const removed = await removeDLQEntry("test-job", "entry-1");

      expect(removed).toBe(true);
      expect(mockRedisLrem).toHaveBeenCalledWith("qstash-dlq:test-job", 1, entry1Str);
    });

    it("returns false when LREM returns 0", async () => {
      mockRedisLrange.mockResolvedValue([JSON.stringify(entry1)]);
      mockRedisLrem.mockResolvedValue(0);

      const { removeDLQEntry } = await import("../dlq");
      const removed = await removeDLQEntry("test-job", "entry-1");

      expect(removed).toBe(false);
    });

    it("returns false when Redis unavailable", async () => {
      const { getRedis } = await import("@/lib/redis");
      vi.mocked(getRedis).mockReturnValueOnce(undefined);

      const { removeDLQEntry } = await import("../dlq");
      const removed = await removeDLQEntry("test-job", "entry-1");

      expect(removed).toBe(false);
    });
  });

  describe("getDLQCount", () => {
    it("returns count for job type", async () => {
      mockRedisLlen.mockResolvedValue(5);

      const { getDLQCount } = await import("../dlq");
      const count = await getDLQCount("notify-collaborators");

      expect(count).toBe(5);
      expect(mockRedisLlen).toHaveBeenCalledWith("qstash-dlq:notify-collaborators");
    });

    it("returns 0 when Redis unavailable", async () => {
      const { getRedis } = await import("@/lib/redis");
      vi.mocked(getRedis).mockReturnValueOnce(undefined);

      const { getDLQCount } = await import("../dlq");
      const count = await getDLQCount("test-job");

      expect(count).toBe(0);
    });
  });
});
