/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryIntent,
  MemoryOrchestratorOptions,
} from "../orchestrator";

// Mock server-only and telemetry before imports
vi.mock("server-only", () => ({}));
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: <T>(_name: string, _opts: unknown, fn: () => Promise<T>) => fn(),
}));

// Dynamic import after mocks
const { runMemoryOrchestrator } = await import("../orchestrator");

/**
 * Create a mock adapter for testing.
 */
function createMockAdapter(
  id: string,
  supportedIntents: MemoryIntent["type"][],
  handler: (
    intent: MemoryIntent,
    ctx: MemoryAdapterContext
  ) => Promise<MemoryAdapterExecutionResult>
): MemoryAdapter {
  return {
    handle: handler,
    id,
    supportedIntents,
  };
}

describe("runMemoryOrchestrator", () => {
  const mockClock = vi.fn(() => 1000);

  const baseIntent: MemoryIntent = {
    sessionId: "session-123",
    type: "syncSession",
    userId: "user-456",
  };

  it("returns ok status when all adapters succeed", async () => {
    const adapters = [
      createMockAdapter("supabase", ["syncSession"], async () => ({
        status: "ok",
      })),
      createMockAdapter("upstash", ["syncSession"], async () => ({
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.status).toBe("ok");
    expect(result.results).toHaveLength(2);
    expect(result.results[0]).toMatchObject({
      adapterId: "supabase",
      status: "ok",
    });
    expect(result.results[1]).toMatchObject({
      adapterId: "upstash",
      status: "ok",
    });
  });

  it("skips adapters that don't support the intent type", async () => {
    const adapters = [
      createMockAdapter("supabase", ["syncSession"], async () => ({
        status: "ok",
      })),
      createMockAdapter("mem0", ["fetchContext"], async () => ({
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.status).toBe("ok");
    expect(result.results).toHaveLength(2);
    expect(result.results[0]).toMatchObject({
      adapterId: "supabase",
      status: "ok",
    });
    expect(result.results[1]).toMatchObject({
      adapterId: "mem0",
      status: "skipped",
    });
  });

  it("returns error status when all adapters fail", async () => {
    const adapters = [
      createMockAdapter("supabase", ["syncSession"], async () => ({
        error: "Database error",
        status: "error",
      })),
      createMockAdapter("upstash", ["syncSession"], async () => ({
        error: "Redis error",
        status: "error",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.status).toBe("error");
    expect(result.results[0].error).toBe("Database error");
    expect(result.results[1].error).toBe("Redis error");
  });

  it("returns partial status when some adapters fail", async () => {
    const adapters = [
      createMockAdapter("supabase", ["syncSession"], async () => ({
        status: "ok",
      })),
      createMockAdapter("upstash", ["syncSession"], async () => ({
        error: "Redis error",
        status: "error",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.status).toBe("partial");
    expect(result.results[0].status).toBe("ok");
    expect(result.results[1].status).toBe("error");
  });

  it("handles thrown errors gracefully", async () => {
    const adapters = [
      createMockAdapter("supabase", ["syncSession"], () =>
        Promise.reject(new Error("Unexpected database crash"))
      ),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.status).toBe("error");
    expect(result.results[0]).toMatchObject({
      adapterId: "supabase",
      error: "Unexpected database crash",
      status: "error",
    });
  });

  it("aggregates context items from fetchContext intents", async () => {
    const fetchIntent: MemoryIntent = {
      limit: 10,
      sessionId: "session-123",
      type: "fetchContext",
      userId: "user-456",
    };

    const adapters = [
      createMockAdapter("supabase", ["fetchContext"], async () => ({
        contextItems: [
          { context: "User preferences", score: 0.9 },
          { context: "Past trip to Paris", score: 0.85 },
        ],
        status: "ok",
      })),
      createMockAdapter("mem0", ["fetchContext"], async () => ({
        contextItems: [{ context: "AI-enriched context", score: 0.75 }],
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(fetchIntent, options);

    expect(result.status).toBe("ok");
    expect(result.context).toHaveLength(3);
    expect(result.context).toContainEqual({
      context: "User preferences",
      score: 0.9,
    });
    expect(result.context).toContainEqual({
      context: "AI-enriched context",
      score: 0.75,
    });
  });

  it("does not include context for non-fetchContext intents", async () => {
    const adapters = [
      createMockAdapter("supabase", ["syncSession"], async () => ({
        contextItems: [{ context: "Should not appear", score: 0.8 }],
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.context).toBeUndefined();
  });

  it("records duration for each adapter execution", async () => {
    let callCount = 0;
    const mockClockIncrementing = () => {
      callCount++;
      return callCount * 100;
    };

    const adapters = [
      createMockAdapter("supabase", ["syncSession"], async () => ({
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClockIncrementing,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.results[0].durationMs).toBeDefined();
    expect(typeof result.results[0].durationMs).toBe("number");
  });

  it("preserves intent information in result", async () => {
    const adapters = [
      createMockAdapter("supabase", ["syncSession"], async () => ({
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    const result = await runMemoryOrchestrator(baseIntent, options);

    expect(result.intent).toEqual(baseIntent);
  });
});

describe("PII redaction", () => {
  const mockClock = vi.fn(() => 1000);

  it("redacts email addresses in turn content for non-canonical adapters", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "Contact me at john@example.com for more info",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let capturedIntent: MemoryIntent | null = null;

    const adapters = [
      createMockAdapter("supabase", ["onTurnCommitted"], (intent) => {
        // Canonical adapter should receive original
        const turnCommit = intent as Extract<MemoryIntent, { type: "onTurnCommitted" }>;
        expect(turnCommit.turn.content).toContain("john@example.com");
        return Promise.resolve({ status: "ok" });
      }),
      createMockAdapter("mem0", ["onTurnCommitted"], (intent) => {
        capturedIntent = intent;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    await runMemoryOrchestrator(turnIntent, options);

    expect(capturedIntent).not.toBeNull();
    const captured = capturedIntent as unknown as Extract<
      MemoryIntent,
      { type: "onTurnCommitted" }
    >;
    expect(captured.turn.content).toContain("[REDACTED]");
    expect(captured.turn.content).not.toContain("john@example.com");
  });

  it("redacts phone numbers in turn content", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "Call me at +1-555-123-4567",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let capturedIntent: MemoryIntent | null = null;

    const adapters = [
      createMockAdapter("mem0", ["onTurnCommitted"], (intent) => {
        capturedIntent = intent;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    await runMemoryOrchestrator(turnIntent, options);

    const captured = capturedIntent as unknown as Extract<
      MemoryIntent,
      { type: "onTurnCommitted" }
    >;
    expect(captured.turn.content).toContain("[REDACTED]");
    expect(captured.turn.content).not.toContain("+1-555-123-4567");
  });

  it("redacts credit card-like numbers in turn content", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "My card number is 4111 1111 1111 1111",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let capturedIntent: MemoryIntent | null = null;

    const adapters = [
      createMockAdapter("upstash", ["onTurnCommitted"], (intent) => {
        capturedIntent = intent;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    await runMemoryOrchestrator(turnIntent, options);

    const captured = capturedIntent as unknown as Extract<
      MemoryIntent,
      { type: "onTurnCommitted" }
    >;
    expect(captured.turn.content).toContain("[REDACTED]");
    expect(captured.turn.content).not.toContain("4111");
  });

  it("does not modify content without PII", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "I want to book a trip to Paris",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let capturedIntent: MemoryIntent | null = null;

    const adapters = [
      createMockAdapter("mem0", ["onTurnCommitted"], (intent) => {
        capturedIntent = intent;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    await runMemoryOrchestrator(turnIntent, options);

    const captured = capturedIntent as unknown as Extract<
      MemoryIntent,
      { type: "onTurnCommitted" }
    >;
    expect(captured.turn.content).toBe("I want to book a trip to Paris");
  });

  it("redacts phone numbers in turn content", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "Call me at +1-555-123-4567",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let capturedIntent: MemoryIntent | null = null;

    const adapters = [
      createMockAdapter("mem0", ["onTurnCommitted"], (intent) => {
        capturedIntent = intent;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    await runMemoryOrchestrator(turnIntent, options);

    const captured = capturedIntent as unknown as Extract<
      MemoryIntent,
      { type: "onTurnCommitted" }
    >;
    expect(captured.turn.content).toContain("[REDACTED]");
    expect(captured.turn.content).not.toContain("+1-555-123-4567");
  });

  it("redacts credit card-like numbers in turn content", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "My card number is 4111 1111 1111 1111",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let capturedIntent: MemoryIntent | null = null;

    const adapters = [
      createMockAdapter("upstash", ["onTurnCommitted"], (intent) => {
        capturedIntent = intent;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    await runMemoryOrchestrator(turnIntent, options);

    const captured = capturedIntent as unknown as Extract<
      MemoryIntent,
      { type: "onTurnCommitted" }
    >;
    expect(captured.turn.content).toContain("[REDACTED]");
    expect(captured.turn.content).not.toContain("4111");
  });

  it("does not modify content without PII", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "I want to book a trip to Paris",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let capturedIntent: MemoryIntent | null = null;

    const adapters = [
      createMockAdapter("mem0", ["onTurnCommitted"], (intent) => {
        capturedIntent = intent;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: mockClock,
    };

    await runMemoryOrchestrator(turnIntent, options);

    const captured = capturedIntent as unknown as Extract<
      MemoryIntent,
      { type: "onTurnCommitted" }
    >;
    expect(captured.turn.content).toBe("I want to book a trip to Paris");
  });

  it("passes original intent to canonical supabase adapter", async () => {
    const turnIntent: MemoryIntent = {
      sessionId: "session-123",
      turn: {
        content: "Contact: user@test.com",
        id: "turn-1",
        role: "user",
        timestamp: "2025-01-01T00:00:00Z",
      },
      type: "onTurnCommitted",
      userId: "user-456",
    };

    let supabaseContent: string | null = null;
    let mem0Content: string | null = null;

    const adapters = [
      createMockAdapter("supabase", ["onTurnCommitted"], (intent) => {
        const turnCommit = intent as Extract<MemoryIntent, { type: "onTurnCommitted" }>;
        supabaseContent = turnCommit.turn.content;
        return Promise.resolve({ status: "ok" });
      }),
      createMockAdapter("mem0", ["onTurnCommitted"], (intent) => {
        const turnCommit = intent as Extract<MemoryIntent, { type: "onTurnCommitted" }>;
        mem0Content = turnCommit.turn.content;
        return Promise.resolve({ status: "ok" });
      }),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: () => 1000,
    };

    await runMemoryOrchestrator(turnIntent, options);

    // Supabase (canonical) gets original
    expect(supabaseContent).toBe("Contact: user@test.com");
    // Mem0 (non-canonical) gets redacted
    expect(mem0Content).toContain("[REDACTED]");
    expect(mem0Content).not.toContain("user@test.com");
  });
});

describe("edge cases", () => {
  it("handles empty adapter list", async () => {
    const intent: MemoryIntent = {
      sessionId: "session-123",
      type: "syncSession",
      userId: "user-456",
    };

    const options: MemoryOrchestratorOptions = {
      adapters: [],
      clock: () => 1000,
    };

    const result = await runMemoryOrchestrator(intent, options);

    expect(result.status).toBe("ok");
    expect(result.results).toHaveLength(0);
  });

  it("handles all adapters skipped", async () => {
    const intent: MemoryIntent = {
      sessionId: "session-123",
      type: "syncSession",
      userId: "user-456",
    };

    const adapters = [
      createMockAdapter("mem0", ["fetchContext"], async () => ({
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: () => 1000,
    };

    const result = await runMemoryOrchestrator(intent, options);

    expect(result.status).toBe("ok");
    expect(result.results).toHaveLength(1);
    expect(result.results[0].status).toBe("skipped");
  });

  it("handles backfillSession intent", async () => {
    const intent: MemoryIntent = {
      sessionId: "session-123",
      type: "backfillSession",
      userId: "user-456",
    };

    const adapters = [
      createMockAdapter("supabase", ["backfillSession"], async () => ({
        status: "ok",
      })),
    ];

    const options: MemoryOrchestratorOptions = {
      adapters,
      clock: () => 1000,
    };

    const result = await runMemoryOrchestrator(intent, options);

    expect(result.status).toBe("ok");
    expect(result.intent.type).toBe("backfillSession");
  });
});
