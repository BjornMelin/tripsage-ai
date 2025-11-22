/** @vitest-environment node */

import type { AgentConfig } from "@schemas/configuration";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";

const mockGetCachedJson = vi.fn();
const mockSetCachedJson = vi.fn();
const mockVersionedKey = vi.fn();
const mockEmitAlert = vi.fn();
const mockRecordEvent = vi.fn();

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: mockGetCachedJson,
  setCachedJson: mockSetCachedJson,
}));

vi.mock("@/lib/cache/tags", () => ({
  versionedKey: mockVersionedKey,
}));

vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: mockEmitAlert,
}));

vi.mock("@/lib/telemetry/span", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/telemetry/span")>(
      "@/lib/telemetry/span"
    );
  return {
    ...actual,
    recordTelemetryEvent: mockRecordEvent,
    withTelemetrySpan: (
      _name: string,
      _opts: { attributes?: Record<string, unknown> },
      fn: () => Promise<unknown>
    ) => fn(),
  };
});

const supabaseSelect = vi.fn();
const supabaseMaybeSingle = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    from: () => ({ select: supabaseSelect }),
  })),
}));

const baseConfig: AgentConfig = {
  agentType: "budgetAgent",
  createdAt: new Date().toISOString(),
  id: "v1732250000_deadbeef",
  model: "gpt-4o",
  parameters: { temperature: 0.4 },
  scope: "global",
  updatedAt: new Date().toISOString(),
};

describe("resolveAgentConfig", () => {
  beforeEach(() => {
    mockGetCachedJson.mockReset();
    mockSetCachedJson.mockReset();
    mockVersionedKey.mockReset();
    mockEmitAlert.mockReset();
    mockRecordEvent.mockReset();
    supabaseSelect.mockReset();
    supabaseMaybeSingle.mockReset();
  });

  it("returns cached value when present", async () => {
    mockVersionedKey.mockResolvedValue("tag:v1:agent:budgetAgent:global");
    mockGetCachedJson.mockResolvedValue({
      config: baseConfig,
      versionId: "v1732250000_deadbeef",
    });

    const result = await resolveAgentConfig("budgetAgent");

    expect(result.config.model).toBe("gpt-4o");
    expect(mockSetCachedJson).not.toHaveBeenCalled();
    expect(supabaseSelect).not.toHaveBeenCalled();
  });

  it("fetches from Supabase and caches on miss", async () => {
    mockVersionedKey.mockResolvedValue("tag:v2:agent:budgetAgent:global");
    mockGetCachedJson.mockResolvedValue(null);
    supabaseSelect.mockReturnValue({
      eq: () => ({ eq: () => ({ maybeSingle: supabaseMaybeSingle }) }),
    });
    supabaseMaybeSingle.mockResolvedValue({
      data: { config: baseConfig, version_id: "v1732250001_cafebabe" },
      error: null,
    });

    const result = await resolveAgentConfig("budgetAgent");

    expect(result.versionId).toBe("v1732250001_cafebabe");
    expect(mockSetCachedJson).toHaveBeenCalledWith(
      "tag:v2:agent:budgetAgent:global",
      { config: baseConfig, versionId: "v1732250001_cafebabe" },
      expect.any(Number)
    );
  });

  it("throws and alerts when schema invalid", async () => {
    mockVersionedKey.mockResolvedValue("tag:v3:agent:budgetAgent:global");
    mockGetCachedJson.mockResolvedValue(null);
    supabaseSelect.mockReturnValue({
      eq: () => ({ eq: () => ({ maybeSingle: supabaseMaybeSingle }) }),
    });
    supabaseMaybeSingle.mockResolvedValue({
      data: { config: { ...baseConfig, model: "invalid-model" }, version_id: "bad" },
      error: null,
    });

    await expect(resolveAgentConfig("budgetAgent")).rejects.toBeTruthy();
    expect(mockEmitAlert).toHaveBeenCalled();
    expect(mockRecordEvent).toHaveBeenCalled();
  });
});
