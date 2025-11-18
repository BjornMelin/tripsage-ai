/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "../route";

// Mock external dependencies
vi.mock("@upstash/qstash", () => {
  const mockVerify = vi.fn().mockResolvedValue(true);
  // Mock Receiver as a class constructor
  class MockReceiver {
    verify = mockVerify;
  }
  return {
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

vi.mock("@/lib/supabase/server", () => {
  // Create a factory function for the from() mock to ensure fresh instances
  const createFromMock = () => {
    const insertMock = vi.fn(() => ({
      select: vi.fn().mockResolvedValue({
        data: [{ id: 1, created_at: "2024-01-01T00:00:00Z" }],
        error: null,
      }),
    }));

    const selectMock = vi.fn(() => ({
      eq: vi.fn(() => ({
        single: vi.fn().mockResolvedValue({
          data: { id: "session-123" },
          error: null,
        }),
      })),
    }));

    const updateMock = vi.fn(() => ({
      eq: vi.fn().mockResolvedValue({
        data: null,
        error: null,
      }),
    }));

    return {
      insert: insertMock,
      select: selectMock,
      update: updateMock,
    };
  };

  return {
    createServerSupabase: vi.fn(() =>
      Promise.resolve({
        from: createFromMock,
      })
    ),
  };
});

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _opts, fn) =>
    fn({
      end: vi.fn(),
      recordException: vi.fn(),
      setStatus: vi.fn(),
    })
  ),
}));

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
    // Reset mocks but preserve implementations
    vi.resetAllMocks();
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
        sessionId: "session-123",
        syncType: "conversation" as const,
        userId: "user-456",
      },
    };

    const req = mockRequest(payload);
    const response = await POST(req);
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
        sessionId: "session-123",
        syncType: "conversation" as const,
        userId: "user-456",
      },
    };

    // Mock receiver to reject signature - override the verify method
    const { Receiver } = await import("@upstash/qstash");
    const originalVerify = Receiver.prototype.verify;
    Receiver.prototype.verify = vi.fn().mockResolvedValue(false);

    const req = mockRequest(payload, "invalid-sig");
    const response = await POST(req);
    const result = await response.json();

    // Restore original verify
    Receiver.prototype.verify = originalVerify;

    expect(response.status).toBe(401);
    expect(result.error).toBe("invalid qstash signature");
  });

  it("rejects invalid job payload", async () => {
    const invalidPayload = {
      invalidField: "value",
    };

    const req = mockRequest(invalidPayload);
    const response = await POST(req);
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
        sessionId: "session-123",
        syncType: "conversation" as const,
        userId: "user-456",
      },
    };

    const req = mockRequest(payload);
    const response = await POST(req);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.duplicate).toBe(true);
    expect(result.ok).toBe(true);
  });

  it("handles session not found error", async () => {
    const { createServerSupabase } = await import("@/lib/supabase/server");
    const mockSupabase = await createServerSupabase();
    (mockSupabase.from as ReturnType<typeof vi.fn>).mockReturnValue({
      select: () => ({
        eq: () => ({
          single: () =>
            Promise.resolve({
              data: null,
              error: { message: "not found" },
            }),
        }),
      }),
    });

    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        sessionId: "invalid-session",
        syncType: "conversation" as const,
        userId: "user-456",
      },
    };

    const req = mockRequest(payload);
    const response = await POST(req);

    expect(response.status).toBe(500);
  });

  it("limits batch size to 50 messages", async () => {
    const messages = Array.from({ length: 60 }, (_, i) => ({
      content: `Message ${i}`,
      role: "user" as const,
      timestamp: "2024-01-01T00:00:00Z",
    }));

    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        conversationMessages: messages,
        sessionId: "session-123",
        syncType: "conversation" as const,
        userId: "user-456",
      },
    };

    const req = mockRequest(payload);
    const response = await POST(req);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.memoriesStored).toBe(50); // Should be limited to 50
  });

  it("handles incremental sync type", async () => {
    const payload = {
      idempotencyKey: "test-key-123",
      payload: {
        sessionId: "session-123",
        syncType: "incremental" as const,
        userId: "user-456",
      },
    };

    const req = mockRequest(payload);
    const response = await POST(req);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.contextUpdated).toBe(true);
    expect(result.syncType).toBe("incremental");
  });
});
