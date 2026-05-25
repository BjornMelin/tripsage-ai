/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const adminClient = vi.hoisted(() => ({}));
const getMaybeSingleMock = vi.hoisted(() => vi.fn());
const insertSingleMock = vi.hoisted(() => vi.fn());
const updateSingleMock = vi.hoisted(() => vi.fn());
const nowIsoMock = vi.hoisted(() => vi.fn(() => "2026-02-03T04:05:06.000Z"));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: vi.fn(() => adminClient),
}));

vi.mock("@/lib/supabase/typed-helpers", () => ({
  getMany: vi.fn(),
  getMaybeSingle: getMaybeSingleMock,
  insertSingle: insertSingleMock,
  updateSingle: updateSingleMock,
}));

vi.mock("@/lib/security/random", () => ({
  nowIso: nowIsoMock,
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => ({
    info: vi.fn(),
    warn: vi.fn(),
  })),
}));

import { createSupabaseMemoryAdapter } from "../supabase-adapter";

describe("createSupabaseMemoryAdapter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getMaybeSingleMock.mockResolvedValue({ data: { id: "session-1" }, error: null });
    insertSingleMock.mockResolvedValue({ data: { id: "turn-1" }, error: null });
    updateSingleMock.mockResolvedValue({ data: { id: "session-1" }, error: null });
  });

  it("uses the shared timestamp helper when syncing sessions", async () => {
    const adapter = createSupabaseMemoryAdapter();

    const result = await adapter.handle(
      {
        sessionId: "session-1",
        type: "syncSession",
        userId: "user-1",
      },
      { now: () => 123 }
    );

    expect(result.status).toBe("ok");
    expect(updateSingleMock).toHaveBeenCalledWith(
      adminClient,
      "sessions",
      { last_synced_at: "2026-02-03T04:05:06.000Z" },
      expect.any(Function),
      { schema: "memories", select: "id", validate: false }
    );
    expect(nowIsoMock).toHaveBeenCalledOnce();
  });

  it("uses the shared timestamp helper after committing a turn", async () => {
    const adapter = createSupabaseMemoryAdapter();

    const result = await adapter.handle(
      {
        sessionId: "session-1",
        turn: {
          content: "Trip memory",
          id: "turn-1",
          role: "user",
          timestamp: "2026-02-03T04:00:00.000Z",
        },
        type: "onTurnCommitted",
        userId: "user-1",
      },
      { now: () => 123 }
    );

    expect(result.status).toBe("ok");
    expect(insertSingleMock).toHaveBeenCalledWith(
      adminClient,
      "turns",
      expect.objectContaining({
        content: { text: "Trip memory" },
        session_id: "session-1",
        user_id: "user-1",
      }),
      { schema: "memories", select: "id", validate: false }
    );
    expect(updateSingleMock).toHaveBeenCalledWith(
      adminClient,
      "sessions",
      { last_synced_at: "2026-02-03T04:05:06.000Z" },
      expect.any(Function),
      { schema: "memories", select: "id", validate: false }
    );
    expect(nowIsoMock).toHaveBeenCalledOnce();
  });
});
