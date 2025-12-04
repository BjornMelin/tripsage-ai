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
    mockEmit.mockReset();
  });

  // TODO: Re-implement GET/PUT/versions/rollback tests with proper hoisted mocks
  // (Legacy skipped tests removed per zero-legacy-tolerance policy)

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
