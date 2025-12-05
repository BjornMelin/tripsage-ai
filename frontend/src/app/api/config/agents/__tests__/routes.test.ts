/** @vitest-environment node */
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/helpers/api-route";

vi.mock("@/lib/cache/tags", () => ({
  bumpTag: vi.fn(async () => 1),
  versionedKey: vi.fn(async (_t: string, k: string) => k),
}));

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn(async () => null),
  setCachedJson: vi.fn(async () => undefined),
}));

const mockEmit = vi.fn();
vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: mockEmit,
}));

vi.mock("@/lib/telemetry/span", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/telemetry/span")>(
      "@/lib/telemetry/span"
    );
  return {
    ...actual,
    withTelemetrySpan: (_n: string, _o: unknown, fn: () => Promise<unknown>) => fn(),
  };
});

const mockResolveAgentConfig = vi.fn();
vi.mock("@/lib/agents/config-resolver", () => ({
  resolveAgentConfig: (...args: unknown[]) => mockResolveAgentConfig(...args),
}));

const supabaseData = {
  config: {
    agentType: "budgetAgent",
    createdAt: new Date().toISOString(),
    id: "v1732250000_deadbeef",
    model: "gpt-4o",
    parameters: { maxTokens: 1000, temperature: 0.3, topP: 0.9 },
    scope: "global",
    updatedAt: new Date().toISOString(),
  },
  version_id: "ver-1",
};

const supabaseSelect = vi.fn();
const supabaseMaybeSingle = vi.fn();
const supabaseInsert = vi.fn();

vi.mock("@/lib/api/factory", () => ({
  setRateLimitFactoryForTests: vi.fn(),
  setSupabaseFactoryForTests: vi.fn(),
  withApiGuards:
    (_config: unknown) =>
    (
      handler: (
        req: Request,
        context?: unknown,
        data?: unknown,
        routeContext?: { params?: unknown }
      ) => unknown
    ) =>
    (req: Request, routeContext: { params?: unknown }) =>
      handler(req, routeContext as unknown, undefined, routeContext),
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: { app_metadata: { is_admin: true }, id: "admin-user" } },
        error: null,
      })),
    },
    from: () => ({
      eq: () => ({ eq: () => ({ maybeSingle: supabaseMaybeSingle }) }),
      insert: supabaseInsert,
      limit: () => ({}) as unknown,
      order: () => ({ data: [], error: null }) as unknown,
      select: supabaseSelect,
    }),
    rpc: vi.fn(async (_fn, _args) => ({
      data: [{ version_id: "ver-2" }],
      error: null,
    })),
  })),
}));

// mockBody removed - was only used by skipped tests

describe("config routes", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({
      app_metadata: { is_admin: true },
      id: "admin-user",
    } as never);
    supabaseSelect.mockReset();
    supabaseMaybeSingle.mockReset();
    supabaseInsert.mockReset();
    supabaseMaybeSingle.mockResolvedValue({ data: supabaseData, error: null });
    mockResolveAgentConfig.mockReset();
    mockEmit.mockReset();
  });

  it("GET resolves and returns agent config", async () => {
    mockResolveAgentConfig.mockResolvedValue({ config: supabaseData.config });
    const { GET } = await import("../[agentType]/route");
    const req = new NextRequest("http://localhost/api/config/agents/budgetAgent");
    const res = await GET(
      req as unknown as NextRequest,
      {
        params: Promise.resolve({ agentType: "budgetAgent" }),
        supabase: {} as never,
        user: { app_metadata: { is_admin: true }, id: "admin-user" } as never,
      } as never
    );

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ config: supabaseData.config });
    expect(mockResolveAgentConfig).toHaveBeenCalledWith("budgetAgent", {
      scope: "global",
      supabase: expect.anything(),
    });
  });

  it("PUT upserts and emits alert", async () => {
    const supabaseRpc = vi.fn().mockResolvedValue({
      data: [{ version_id: "ver-2" }],
      error: null,
    });
    const supabase = {
      from: vi.fn(() => ({
        select: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn(() => ({ maybeSingle: supabaseMaybeSingle })),
          })),
        })),
      })),
      rpc: supabaseRpc,
    } as unknown as {
      from: ReturnType<typeof vi.fn>;
      rpc: ReturnType<typeof vi.fn>;
    };

    supabaseMaybeSingle.mockResolvedValue({
      data: { config: supabaseData.config },
      error: null,
    });

    const body = {
      description: "updated",
      maxTokens: 500,
      model: "gpt-4o-mini",
      temperature: 0.4,
      timeoutSeconds: 30,
      topP: 0.8,
    };

    const { PUT } = await import("../[agentType]/route");
    const req = new NextRequest("http://localhost/api/config/agents/budgetAgent", {
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
      method: "PUT",
    } as never);

    const res = await PUT(
      req as unknown as NextRequest,
      {
        params: Promise.resolve({ agentType: "budgetAgent" }),
        supabase,
        user: { app_metadata: { is_admin: true }, id: "admin-user" } as never,
      } as never
    );

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.versionId).toBe("ver-2");
    expect(mockEmit).toHaveBeenCalledWith(
      "agent_config.updated",
      expect.objectContaining({
        attributes: expect.objectContaining({ agentType: "budgetAgent" }),
      })
    );
    expect(supabaseRpc).toHaveBeenCalledWith(
      "agent_config_upsert",
      expect.objectContaining({
        p_agent_type: "budgetAgent",
        p_config: expect.objectContaining({
          agentType: "budgetAgent",
          parameters: expect.objectContaining({
            maxTokens: body.maxTokens,
            temperature: body.temperature,
            timeoutSeconds: body.timeoutSeconds,
            topP: body.topP,
          }),
        }),
        p_created_by: "admin-user",
        p_scope: "global",
        p_summary: body.description,
      })
    );
  });

  it("versions returns list", async () => {
    const versionsRow = {
      created_at: "2025-12-01T00:00:00Z",
      created_by: "admin-user",
      id: "ver-1",
      scope: "global",
      summary: "initial",
    };

    const supabase = {
      from: vi.fn(() => ({
        select: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn(() => ({
              order: vi.fn(() => ({
                limit: vi.fn(() => ({ data: [versionsRow], error: null })),
              })),
            })),
          })),
        })),
      })),
    } as unknown as { from: ReturnType<typeof vi.fn> };

    const { GET } = await import("../[agentType]/versions/route");
    const req = new NextRequest(
      "http://localhost/api/config/agents/budgetAgent/versions"
    );
    const res = await GET(
      req as unknown as NextRequest,
      {
        params: Promise.resolve({ agentType: "budgetAgent" }),
        supabase,
        user: { app_metadata: { is_admin: true }, id: "admin-user" } as never,
      } as never
    );

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.versions).toHaveLength(1);
    expect(json.versions[0].id).toBe("ver-1");
  });

  it("rollback emits alert", async () => {
    const supabase = {
      from: vi.fn(() => ({
        select: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn(() => ({
              maybeSingle: vi
                .fn()
                .mockResolvedValue({ data: supabaseData, error: null }),
            })),
          })),
        })),
      })),
      rpc: vi.fn(async () => ({ data: [{ version_id: "ver-rollback" }], error: null })),
    } as unknown as {
      from: ReturnType<typeof vi.fn>;
      rpc: ReturnType<typeof vi.fn>;
    };

    const { POST } = await import("../[agentType]/rollback/[versionId]/route");
    const req = new NextRequest(
      "http://localhost/api/config/agents/budgetAgent/rollback/11111111-1111-4111-8111-111111111111"
    );

    const res = await POST(
      req as unknown as NextRequest,
      {
        params: Promise.resolve({
          agentType: "budgetAgent",
          versionId: "11111111-1111-4111-8111-111111111111",
        }),
        supabase,
        user: { app_metadata: { is_admin: true }, id: "admin-user" } as never,
      } as never
    );

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual(
      expect.objectContaining({
        versionId: "ver-rollback",
      })
    );
    expect(mockEmit).toHaveBeenCalledWith(
      "agent_config.rollback",
      expect.objectContaining({
        attributes: expect.objectContaining({ agentType: "budgetAgent" }),
      })
    );
  });

  it("rejects non-admin", async () => {
    mockApiRouteAuthUser({ id: "user" } as never);
    const { GET } = await import("../[agentType]/route");
    const req = new NextRequest("http://localhost/api/config/agents/budgetAgent");
    const res = await GET(
      req as unknown as NextRequest,
      {
        params: Promise.resolve({ agentType: "budgetAgent" }),
        supabase: {} as never,
        user: { id: "user" } as never,
      } as never
    );
    expect(res.status).toBe(403);
  });
});
