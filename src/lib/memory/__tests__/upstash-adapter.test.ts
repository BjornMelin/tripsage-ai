/** @vitest-environment node */

import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { TEST_QSTASH_TOKEN, TEST_REDIS_TOKEN, TEST_REDIS_URL } from "@/test/upstash";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

// Mock server-only boundary for test runtime
vi.mock("server-only", () => ({}));

const { afterAllHook, beforeEachHook, mocks } = setupUpstashTestEnvironment();

const envStore = vi.hoisted<Record<string, string | undefined>>(() => ({}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (key: string) => {
    const value = envStore[key];
    if (!value) throw new Error(`Missing env ${key}`);
    return value;
  },
  getServerEnvVarWithFallback: (key: string, fallback?: string) => {
    return (envStore[key] ?? fallback) as string;
  },
}));

const { createUpstashMemoryAdapter } = await import("../upstash-adapter");

describe("createUpstashMemoryAdapter", () => {
  beforeEach(() => {
    beforeEachHook();
    envStore.NEXT_PUBLIC_SITE_URL = "https://example.test";
    envStore.QSTASH_TOKEN = TEST_QSTASH_TOKEN;
    envStore.UPSTASH_REDIS_REST_TOKEN = TEST_REDIS_TOKEN;
    envStore.UPSTASH_REDIS_REST_URL = TEST_REDIS_URL;
  });

  afterAll(() => {
    afterAllHook();
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
    const messages = mocks.qstash.__getMessages();
    expect(messages).toHaveLength(2);
    for (const message of messages) {
      const body = message.body as { idempotencyKey: string; payload: unknown };
      expect(message.url).toBe("https://example.test/api/jobs/memory-sync");
      expect(body.idempotencyKey).toMatch(/^conv-sync:session-123:turn-1:\d+$/);
      expect(body.payload).toEqual(
        expect.objectContaining({
          sessionId: "session-123",
          syncType: "conversation",
          userId: "user-456",
        })
      );
      expect(message.deduplicationId).toBe(`memory-sync:${body.idempotencyKey}`);
    }
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
    const messages = mocks.qstash.__getMessages();
    expect(messages).toHaveLength(2);
    expect(messages[0]?.body).toEqual({
      idempotencyKey: "incr-sync:session-123",
      payload: {
        sessionId: "session-123",
        syncType: "incremental",
        userId: "user-456",
      },
    });
    expect(messages[0]?.deduplicationId).toBeUndefined();
    expect(messages[1]?.body).toEqual({
      idempotencyKey: "full-sync:session-123",
      payload: {
        sessionId: "session-123",
        syncType: "full",
        userId: "user-456",
      },
    });
    expect(messages[1]?.deduplicationId).toBeUndefined();
  });
});
