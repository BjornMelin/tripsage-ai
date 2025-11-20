/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

// Mock external dependencies
vi.mock("@upstash/qstash", () => {
  const mockVerify = vi.fn().mockResolvedValue(true);
  // Mock Receiver as a class constructor
  class MockReceiver {
    // Prototype method so tests can override via prototype or mockVerify
    async verify(...args: unknown[]) {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-return
      return await mockVerify(...args);
    }
  }
  return {
    mockVerify,
    Receiver: MockReceiver,
  };
});

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: vi.fn(() => "test-current-key"),
  getServerEnvVarWithFallback: vi.fn(() => "test-next-key"),
}));

vi.mock("@/lib/idempotency/redis", () => ({
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
      return {
        insert: vi.fn(() => ({
          select: vi.fn().mockResolvedValue({
            data: [{ id: 1 }],
            error: null,
          }),
        })),
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
  withTelemetrySpan: vi.fn((_name, _opts, fn) => {
    const span = {
      end: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
      setStatus: vi.fn(),
    };
    try {
      return fn(span);
    } catch (error) {
      // eslint-disable-next-line no-console
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
  tryReserveKeyMock = tryReserveKey as unknown as ReturnType<typeof vi.fn>;
});

describe("POST /api/jobs/memory-sync", () => {
  const mockRequest = (body: unknown, signature = "valid-sig") => {
    return new NextRequest("http://localhost/api/jobs/memory-sync", {
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
        "Upstash-Signature": signature,
      },
      method: "POST",
    });
  };

  beforeEach(() => {
    // Reset MOCK_FROM to default implementation before each test
    MOCK_FROM.mockImplementation(createDefaultFromMock);
    tryReserveKeyMock.mockResolvedValue(true);
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

    const { mockVerify } = await import("@upstash/qstash");
    mockVerify.mockResolvedValueOnce(false);

    const req = mockRequest(payload, "invalid-sig");
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(401);
    expect(result.error).toBe("invalid qstash signature");
  });

  it("rejects invalid job payload", async () => {
    const invalidPayload = {
      invalidField: "value",
    };

    const req = mockRequest(invalidPayload);
    const response = await post(req);
    const result = await response.json();

    expect(response.status).toBe(400);
    expect(result.error).toBe("invalid job payload");
  });

  it("handles duplicate jobs gracefully", async () => {
    const { tryReserveKey } = await import("@/lib/idempotency/redis");
    (tryReserveKey as ReturnType<typeof vi.fn>).mockResolvedValue(false); // Simulate duplicate

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

  it("handles session not found error", async () => {
    MOCK_FROM.mockImplementation((table: string) => {
      if (table === "chat_sessions") {
        return {
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
        } as unknown as ReturnType<typeof createDefaultFromMock>;
      }
      return createDefaultFromMock(table as string) as unknown as ReturnType<
        typeof createDefaultFromMock
      >;
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
    const _result = await response.json();

    expect(response.status).toBe(500);
  });

  it("limits batch size to 50 messages", async () => {
    // Override the memories insert mock to return 50 items
    MOCK_FROM.mockImplementation((table: string) => {
      if (table === "chat_sessions") {
        return {
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
        } as unknown as ReturnType<typeof createDefaultFromMock>;
      }
      if (table === "memories") {
        return {
          insert: vi.fn(() => ({
            select: vi.fn().mockResolvedValue({
              data: Array.from({ length: 50 }, (_, i) => ({
                created_at: "2024-01-01T00:00:00Z",
                id: i + 1,
              })),
              error: null,
            }),
          })),
        } as unknown as ReturnType<typeof createDefaultFromMock>;
      }
      return createDefaultFromMock(table as string) as unknown as ReturnType<
        typeof createDefaultFromMock
      >;
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
});
