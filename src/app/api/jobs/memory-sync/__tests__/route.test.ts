/** @vitest-environment node */

import { NextRequest } from "next/server";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

const {
  afterAllHook: upstashAfterAllHook,
  beforeEachHook: upstashBeforeEachHook,
  mocks: upstashMocks,
} = setupUpstashTestEnvironment();

// Mock external dependencies
vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: vi.fn(() => "test-current-key"),
  getServerEnvVarWithFallback: vi.fn(() => "test-next-key"),
}));

type ReleaseKey = (key: string, options?: unknown) => Promise<boolean>;
const releaseKeyMock = vi.hoisted(() => vi.fn<ReleaseKey>(async () => true));

vi.mock("@/lib/idempotency/redis", () => ({
  releaseKey: (key: string, options?: unknown) => releaseKeyMock(key, options),
  tryReserveKey: vi.fn().mockResolvedValue(true),
}));

// Hoist mock functions so they can be accessed and modified in tests
const createDefaultFromMock = vi.hoisted(() => {
  const sessionId = "123e4567-e89b-12d3-a456-426614174000";
  // Create query builder that supports chaining with .eq().eq().single()
  const createSelectBuilder = () => {
    const builder: {
      eq: ReturnType<typeof vi.fn>;
      single: ReturnType<typeof vi.fn>;
    } = {
      eq: vi.fn(),
      single: vi.fn().mockResolvedValue({
        data: { id: sessionId },
        error: null,
      }),
    };
    // Make eq return the builder itself for chaining
    builder.eq = vi.fn(() => builder);
    return builder;
  };

  return (table: string) => {
    if (table === "chat_sessions") {
      return {
        select: vi.fn(() => createSelectBuilder()),
        update: vi.fn(() => ({
          eq: vi.fn().mockResolvedValue({
            data: null,
            error: null,
          }),
        })),
      };
    }
    if (table === "sessions") {
      return {
        insert: vi.fn(() => ({
          select: vi.fn().mockResolvedValue({
            data: [{ id: sessionId }],
            error: null,
          }),
        })),
        select: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn(() => ({
              single: vi.fn().mockResolvedValue({
                data: { id: sessionId },
                error: null,
              }),
            })),
          })),
        })),
        update: vi.fn(() => ({
          eq: vi.fn().mockResolvedValue({
            data: null,
            error: null,
          }),
        })),
      };
    }
    if (table === "turns") {
      const createTurnsSelectBuilder = () => {
        const builder: {
          eq: ReturnType<typeof vi.fn>;
          in: ReturnType<typeof vi.fn>;
        } = {
          eq: vi.fn(),
          in: vi.fn().mockResolvedValue({
            data: [],
            error: null,
          }),
        };
        builder.eq = vi.fn(() => builder);
        return builder;
      };
      return {
        insert: vi.fn(() => ({
          select: vi.fn().mockResolvedValue({
            data: [{ id: 1 }],
            error: null,
          }),
        })),
        select: vi.fn(() => createTurnsSelectBuilder()),
      };
    }
    if (table === "memories") {
      return {
        insert: vi.fn(() => ({
          select: vi.fn().mockResolvedValue({
            data: [{ created_at: "2024-01-01T00:00:00Z", id: 1 }],
            error: null,
          }),
        })),
      };
    }
    return {};
  };
});

const MOCK_FROM = vi.hoisted(() => vi.fn(createDefaultFromMock));

type MockFromReturn = ReturnType<typeof createDefaultFromMock>;

vi.mock("@/lib/supabase/server", () => {
  return {
    createServerSupabase: vi.fn(() =>
      Promise.resolve({
        from: MOCK_FROM,
      })
    ),
  };
});

vi.mock("@/lib/supabase/admin", () => {
  return {
    createAdminSupabase: vi.fn(() => ({
      from: MOCK_FROM,
      schema: () => ({
        from: MOCK_FROM,
      }),
    })),
  };
});

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  sanitizeAttributes: vi.fn((attrs) => attrs),
  withTelemetrySpan: vi.fn((_name, _opts, fn) => {
    const span = {
      addEvent: vi.fn(),
      end: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
      setStatus: vi.fn(),
    };
    try {
      return fn(span);
    } catch (error) {
      console.error("withTelemetrySpan error", error);
      throw error;
    }
  }),
}));

let post: typeof import("../route").POST;
let tryReserveKeyMock: ReturnType<typeof vi.fn>;

beforeAll(async () => {
  ({ POST: post } = await import("../route"));
  const { tryReserveKey } = await import("@/lib/idempotency/redis");
  tryReserveKeyMock = unsafeCast<ReturnType<typeof vi.fn>>(tryReserveKey);
});

describe("POST /api/jobs/memory-sync", () => {
  const mockRequest = (
    body: unknown,
    {
      signature = "valid-sig",
      messageId = "msg-1",
    }: { signature?: string; messageId?: string } = {}
  ) => {
    return new NextRequest("http://localhost/api/jobs/memory-sync", {
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
        "Upstash-Message-Id": messageId,
        "Upstash-Signature": signature,
      },
      method: "POST",
    });
  };

  beforeEach(() => {
    upstashBeforeEachHook();
    // Reset MOCK_FROM to default implementation before each test
    MOCK_FROM.mockImplementation(createDefaultFromMock);
    tryReserveKeyMock.mockResolvedValue(true);
    releaseKeyMock.mockReset();
  });

  it("processes valid memory sync job successfully", async () => {
    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        conversationMessages: [
          {
            content: "Hello world",
            role: "user" as const,
            timestamp: "2024-01-01T00:00:00Z",
          },
        ],
        sessionId: "123e4567-e89b-12d3-a456-426614174000",
        syncType: "conversation" as const,
        userId: "11111111-1111-4111-8111-111111111111",
      },
    };

    const req = mockRequest(payload);
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.ok).toBe(true);
    expect(result.memoriesStored).toBe(1);
    expect(result.contextUpdated).toBe(true);
  });

  it("rejects invalid signature", async () => {
    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        sessionId: "123e4567-e89b-12d3-a456-426614174000",
        syncType: "conversation" as const,
        userId: "11111111-1111-4111-8111-111111111111",
      },
    };

    upstashMocks.qstash.__forceVerify(false);

    const req = mockRequest(payload, { signature: "invalid-sig" });
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(401);
    expect(result.error).toBe("unauthorized");
    expect(result.reason).toBe("Invalid Upstash signature");
  });

  it("rejects invalid job payload", async () => {
    const invalidPayload = {
      invalidField: "value",
    };

    const req = mockRequest(invalidPayload);
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(489);
    expect(result.error).toBe("invalid_request");
    expect(result.reason).toBe("Request validation failed");
    expect(response.headers.get("Upstash-NonRetryable-Error")).toBe("true");
  });

  it("handles duplicate jobs gracefully", async () => {
    tryReserveKeyMock.mockResolvedValue(false); // Simulate duplicate

    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        sessionId: "123e4567-e89b-12d3-a456-426614174000",
        syncType: "conversation" as const,
        userId: "11111111-1111-4111-8111-111111111111",
      },
    };

    const req = mockRequest(payload);
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.duplicate).toBe(true);
    expect(result.ok).toBe(true);
  });

  it("returns duplicate on repeated Upstash-Message-Id without invoking side effects", async () => {
    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        sessionId: "123e4567-e89b-12d3-a456-426614174000",
        syncType: "conversation" as const,
        userId: "11111111-1111-4111-8111-111111111111",
      },
    };

    const res1 = await post(mockRequest(payload, { messageId: "msg-dupe" }));
    expect(res1.status).toBe(200);

    tryReserveKeyMock.mockClear();

    const res2 = await post(mockRequest(payload, { messageId: "msg-dupe" }));
    const json2 = await res2.json();
    expect(res2.status).toBe(200);
    expect(json2.ok).toBe(true);
    expect(json2.duplicate).toBe(true);
    expect(tryReserveKeyMock).not.toHaveBeenCalled();
  });

  it("handles session not found error", async () => {
    MOCK_FROM.mockImplementation((table: string) => {
      if (table === "chat_sessions") {
        return unsafeCast<MockFromReturn>({
          select: vi.fn(() => ({
            eq: vi.fn(() => ({
              eq: vi.fn(() => ({
                single: vi.fn().mockResolvedValue({
                  data: null,
                  error: { message: "not found" },
                }),
              })),
            })),
          })),
        });
      }
      return createDefaultFromMock(table);
    });

    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        sessionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        syncType: "conversation" as const,
        userId: "11111111-1111-4111-8111-111111111111",
      },
    };

    const req = mockRequest(payload);
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(500);
    expect(result.error).toBeDefined();
    expect(releaseKeyMock).toHaveBeenCalledWith("memory-sync:test-key-123", {
      degradedMode: "fail_open",
    });
  });

  it("limits batch size to 50 messages", async () => {
    // Override the memories insert mock to return 50 items
    MOCK_FROM.mockImplementation((table: string) => {
      if (table === "chat_sessions") {
        return unsafeCast<MockFromReturn>({
          select: vi.fn(() => ({
            eq: vi.fn(() => ({
              eq: vi.fn(() => ({
                single: vi.fn().mockResolvedValue({
                  data: { id: "session-123" },
                  error: null,
                }),
              })),
            })),
          })),
          update: vi.fn(() => ({
            eq: vi.fn().mockResolvedValue({
              data: null,
              error: null,
            }),
          })),
        });
      }
      if (table === "memories") {
        return unsafeCast<MockFromReturn>({
          insert: vi.fn(() => ({
            select: vi.fn().mockResolvedValue({
              data: Array.from({ length: 50 }, (_, i) => ({
                created_at: "2024-01-01T00:00:00Z",
                id: i + 1,
              })),
              error: null,
            }),
          })),
        });
      }
      return createDefaultFromMock(table);
    });

    const messages = Array.from({ length: 60 }, (_, i) => ({
      content: `Message ${i}`,
      role: "user" as const,
      timestamp: "2024-01-01T00:00:00Z",
    }));

    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        conversationMessages: messages,
        sessionId: "123e4567-e89b-12d3-a456-426614174000",
        syncType: "conversation" as const,
        userId: "11111111-1111-4111-8111-111111111111",
      },
    };

    const req = mockRequest(payload);
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.memoriesStored).toBe(50); // Should be limited to 50
  });

  it("handles incremental sync type", async () => {
    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        sessionId: "123e4567-e89b-12d3-a456-426614174000",
        syncType: "incremental" as const,
        userId: "11111111-1111-4111-8111-111111111111",
      },
    };

    const req = mockRequest(payload);
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.contextUpdated).toBe(true);
    expect(result.syncType).toBe("incremental");
    expect(result.memoriesStored).toBe(0);
  });

  afterAll(() => {
    upstashAfterAllHook();
  });
});
