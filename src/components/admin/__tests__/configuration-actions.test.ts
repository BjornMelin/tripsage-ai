/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchAgentBundle } from "../configuration-actions";

const resolveAgentConfigMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/agents/config-resolver", () => ({
  resolveAgentConfig: resolveAgentConfigMock,
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    from: () => ({
      select: vi.fn(),
    }),
  })),
}));

describe("fetchAgentBundle", () => {
  beforeEach(() => {
    resolveAgentConfigMock.mockReset();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns fallback bundle when E2E bypass is enabled", async () => {
    vi.stubEnv("E2E_BYPASS_RATE_LIMIT", "1");
    vi.stubEnv("NODE_ENV", "development");
    resolveAgentConfigMock.mockRejectedValue(new Error("DB unavailable"));

    const result = await fetchAgentBundle("budgetAgent");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.config.agentType).toBe("budgetAgent");
      expect(result.data.metrics.versionCount).toBe(0);
      expect(result.data.versions).toHaveLength(0);
    }
  });

  it("returns agent bundle when resolution succeeds", async () => {
    const { createServerSupabase } = await import("@/lib/supabase/server");
    const config = {
      agentType: "budgetAgent",
      createdAt: "2026-01-01T00:00:00.000Z",
      id: "v1",
      model: "gpt-4o",
      parameters: { model: "gpt-4o" },
      scope: "global",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };

    const versions = [
      {
        created_at: "2026-01-02T00:00:00.000Z",
        created_by: "user-1",
        id: "v1",
        summary: "Initial",
      },
    ];

    const builder = {
      eq: vi.fn(() => builder),
      limit: vi.fn(async () => ({ data: versions, error: null })),
      order: vi.fn(() => builder),
      select: vi.fn(() => builder),
    };

    vi.mocked(createServerSupabase).mockResolvedValue({
      from: vi.fn(() => builder),
    } as never);

    resolveAgentConfigMock.mockResolvedValue({ config });

    const result = await fetchAgentBundle("budgetAgent");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.config.agentType).toBe("budgetAgent");
      expect(result.data.metrics.versionCount).toBe(versions.length);
      expect(result.data.versions).toHaveLength(versions.length);
    }
  });

  it("returns error when bypass is disabled and resolution fails", async () => {
    vi.stubEnv("E2E_BYPASS_RATE_LIMIT", "0");
    vi.stubEnv("NODE_ENV", "development");
    resolveAgentConfigMock.mockRejectedValue(new Error("DB unavailable"));

    const result = await fetchAgentBundle("budgetAgent");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.error).toBe("internal");
    }
  });
});
