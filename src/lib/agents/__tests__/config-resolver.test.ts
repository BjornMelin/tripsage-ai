/** @vitest-environment node */

import type { AgentConfig } from "@schemas/configuration";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getAgentConfigCacheTags,
  invalidateAgentConfigCache,
  resolveAgentConfig,
} from "@/lib/agents/config-resolver";

const mockGetCachedJson = vi.hoisted(() => vi.fn());
const mockSetCachedJson = vi.hoisted(() => vi.fn());
const mockBumpTag = vi.hoisted(() => vi.fn());
const mockVersionedKey = vi.hoisted(() => vi.fn());
const mockCacheLife = vi.hoisted(() => vi.fn());
const mockCacheTag = vi.hoisted(() => vi.fn());
const mockRevalidateTag = vi.hoisted(() => vi.fn());
const mockEmitAlert = vi.hoisted(() => vi.fn());
const mockRecordEvent = vi.hoisted(() => vi.fn());

vi.mock("next/cache", () => ({
  cacheLife: mockCacheLife,
  cacheTag: mockCacheTag,
  revalidateTag: mockRevalidateTag,
}));

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: mockGetCachedJson,
  setCachedJson: mockSetCachedJson,
}));

vi.mock("@/lib/cache/tags", () => ({
  bumpTag: mockBumpTag,
  versionedKey: mockVersionedKey,
}));

vi.mock("@/lib/telemetry/degraded-mode", () => ({
  emitOperationalAlertOncePerWindow: (...args: unknown[]) => mockEmitAlert(...args),
  resetDegradedModeAlertStateForTests: () => undefined,
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

const supabaseSelect = vi.hoisted(() => vi.fn());
const supabaseMaybeSingle = vi.hoisted(() => vi.fn());

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: vi.fn((key: string) => {
    if (key === "NEXT_PUBLIC_SUPABASE_URL") return "https://test.supabase.co";
    if (key === "SUPABASE_SERVICE_ROLE_KEY") return "test-service-role-key";
    return undefined;
  }),
  getServerEnvVarWithFallback: vi.fn((key: string, fallback?: string) => {
    if (key === "NEXT_PUBLIC_SUPABASE_URL") return "https://test.supabase.co";
    if (key === "SUPABASE_SERVICE_ROLE_KEY") return "test-service-role-key";
    return fallback;
  }),
}));

const mockCreateAdminSupabase = vi.hoisted(() =>
  vi.fn(() => ({
    from: () => ({ select: supabaseSelect }),
  }))
);

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: mockCreateAdminSupabase,
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    from: () => ({ select: supabaseSelect }),
  })),
}));

const baseConfig: AgentConfig = {
  agentType: "budgetAgent",
  createdAt: new Date().toISOString(),
  id: "v1732250000_deadbeef",
  model: "gpt-5.5",
  parameters: { temperature: 0.4 },
  scope: "global",
  updatedAt: new Date().toISOString(),
};

describe("resolveAgentConfig", () => {
  beforeEach(() => {
    mockGetCachedJson.mockReset();
    mockSetCachedJson.mockReset();
    mockBumpTag.mockReset();
    mockVersionedKey.mockReset();
    mockCacheLife.mockReset();
    mockCacheTag.mockReset();
    mockRevalidateTag.mockReset();
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

    expect(result.config.model).toBe("gpt-5.5");
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
      data: {
        config: { ...baseConfig, model: "https://models.test/gpt" },
        version_id: "bad",
      },
      error: null,
    });

    await expect(resolveAgentConfig("budgetAgent")).rejects.toBeTruthy();
    expect(mockEmitAlert).toHaveBeenCalled();
    expect(mockRecordEvent).toHaveBeenCalled();
  });

  it("invalidates every agent config cache tag", async () => {
    mockBumpTag.mockResolvedValue(2);

    await invalidateAgentConfigCache("budgetAgent", "global");

    expect(mockBumpTag).toHaveBeenCalledWith("configuration");
    expect(mockRevalidateTag).toHaveBeenCalledTimes(3);
    expect(mockRevalidateTag).toHaveBeenNthCalledWith(1, "configuration", {
      expire: 0,
    });
    expect(mockRevalidateTag).toHaveBeenNthCalledWith(2, "configuration:budgetAgent", {
      expire: 0,
    });
    expect(mockRevalidateTag).toHaveBeenNthCalledWith(
      3,
      "configuration:budgetAgent:global",
      { expire: 0 }
    );
  });

  it("keeps the cache tag tuple stable for routes and resolver", () => {
    expect(getAgentConfigCacheTags("budgetAgent", "global")).toEqual([
      "configuration",
      "configuration:budgetAgent",
      "configuration:budgetAgent:global",
    ]);
  });
});
