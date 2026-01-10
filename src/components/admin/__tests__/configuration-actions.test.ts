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
});
