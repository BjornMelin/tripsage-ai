/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock server-only boundary for test runtime
vi.mock("server-only", () => ({}));

type TryEnqueueJob = (
  jobType: string,
  payload: unknown,
  path: string,
  options?: unknown
) => Promise<
  { messageId: string; success: true } | { error: Error | null; success: false }
>;

const tryEnqueueJobMock = vi.hoisted(() =>
  vi.fn<TryEnqueueJob>(async () => ({ messageId: "msg-1", success: true }))
);

vi.mock("@/lib/qstash/client", () => ({
  tryEnqueueJob: (jobType: string, payload: unknown, path: string, options?: unknown) =>
    tryEnqueueJobMock(jobType, payload, path, options),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: () => null,
}));

const { createUpstashMemoryAdapter } = await import("../upstash-adapter");

describe("createUpstashMemoryAdapter", () => {
  beforeEach(() => {
    tryEnqueueJobMock.mockClear();
  });

  it("uses stable idempotency keys for onTurnCommitted sync", async () => {
    const adapter = createUpstashMemoryAdapter();
    const ctx = { now: () => Date.now() };

    const intent = {
      sessionId: "session-123",
      turn: {
        content: "Hello world",
        id: "turn-1",
        role: "user" as const,
        timestamp: "2024-01-01T00:00:00Z",
      },
      type: "onTurnCommitted" as const,
      userId: "user-456",
    };

    const first = await adapter.handle(intent, ctx);
    const second = await adapter.handle(intent, ctx);

    expect(first.status).toBe("ok");
    expect(second.status).toBe("ok");
    expect(tryEnqueueJobMock).toHaveBeenCalledTimes(2);
    expect(tryEnqueueJobMock).toHaveBeenNthCalledWith(
      1,
      "memory-sync",
      expect.objectContaining({
        idempotencyKey: "conv-sync:session-123:turn-1",
        payload: expect.objectContaining({
          sessionId: "session-123",
          syncType: "conversation",
          userId: "user-456",
        }),
      }),
      "/api/jobs/memory-sync",
      expect.objectContaining({
        deduplicationId: "memory-sync:conv-sync:session-123:turn-1",
      })
    );
    expect(tryEnqueueJobMock).toHaveBeenNthCalledWith(
      2,
      "memory-sync",
      expect.objectContaining({
        idempotencyKey: "conv-sync:session-123:turn-1",
      }),
      "/api/jobs/memory-sync",
      expect.objectContaining({
        deduplicationId: "memory-sync:conv-sync:session-123:turn-1",
      })
    );
  });

  it("uses stable idempotency keys for syncSession/backfillSession", async () => {
    const adapter = createUpstashMemoryAdapter();
    const ctx = { now: () => Date.now() };

    const syncIntent = {
      sessionId: "session-123",
      type: "syncSession" as const,
      userId: "user-456",
    };
    const backfillIntent = {
      sessionId: "session-123",
      type: "backfillSession" as const,
      userId: "user-456",
    };

    const syncResult = await adapter.handle(syncIntent, ctx);
    const backfillResult = await adapter.handle(backfillIntent, ctx);

    expect(syncResult.status).toBe("ok");
    expect(backfillResult.status).toBe("ok");
    expect(tryEnqueueJobMock).toHaveBeenNthCalledWith(
      1,
      "memory-sync",
      {
        idempotencyKey: "incr-sync:session-123",
        payload: {
          sessionId: "session-123",
          syncType: "incremental",
          userId: "user-456",
        },
      },
      "/api/jobs/memory-sync",
      expect.objectContaining({
        deduplicationId: "memory-sync:incr-sync:session-123",
      })
    );
    expect(tryEnqueueJobMock).toHaveBeenNthCalledWith(
      2,
      "memory-sync",
      {
        idempotencyKey: "full-sync:session-123",
        payload: {
          sessionId: "session-123",
          syncType: "full",
          userId: "user-456",
        },
      },
      "/api/jobs/memory-sync",
      expect.objectContaining({
        deduplicationId: "memory-sync:full-sync:session-123",
      })
    );
  });
});
