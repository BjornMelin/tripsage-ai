/** @vitest-environment node */
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/api-route-helpers";

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
    (handler: (req: Request, routeContext: { params?: unknown }) => unknown) =>
    (req: Request, routeContext: { params?: unknown }) =>
      handler(req, routeContext),
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

const mockBody = {
  maxTokens: 1200,
  temperature: 0.4,
};

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
    mockEmit.mockReset();
  });

  it.skip("GET returns cached miss + db result", async () => {
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
    const json = await res.json();
    expect(json.versionId).toBe("ver-1");
  });

  it.skip("PUT upserts and emits alert", async () => {
    const { PUT } = await import("../[agentType]/route");
    const req = new NextRequest("http://localhost/api/config/agents/budgetAgent", {
      body: JSON.stringify(mockBody),
      headers: { "Content-Type": "application/json" },
      method: "PUT",
    } as never);
    const res = await PUT(
      req as unknown as NextRequest,
      {
        params: Promise.resolve({ agentType: "budgetAgent" }),
        supabase: {} as never,
        user: { app_metadata: { is_admin: true }, id: "admin-user" } as never,
      } as never
    );
    expect(res.status).toBe(200);
    expect(mockEmit).toHaveBeenCalledWith(
      "agent_config.updated",
      expect.objectContaining({
        attributes: expect.objectContaining({ agentType: "budgetAgent" }),
      })
    );
  });

  it.skip("versions returns list", async () => {
    supabaseSelect.mockReturnValue({
      eq: () => ({
        eq: () => ({
          order: () => ({ limit: () => ({ data: [], error: null }) }),
        }),
      }),
    });
    const { GET } = await import("../[agentType]/versions/route");
    const req = new NextRequest(
      "http://localhost/api/config/agents/budgetAgent/versions"
    );
    const res = await GET(
      req as unknown as NextRequest,
      {
        params: Promise.resolve({ agentType: "budgetAgent" }),
        supabase: {} as never,
        user: { app_metadata: { is_admin: true }, id: "admin-user" } as never,
      } as never
    );
    expect(res.status).toBe(200);
  });

  it.skip("rollback emits alert", async () => {
    supabaseMaybeSingle.mockResolvedValue({ data: supabaseData, error: null });
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
        supabase: {} as never,
        user: { app_metadata: { is_admin: true }, id: "admin-user" } as never,
      } as never
    );
    expect(res.status).toBe(200);
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
