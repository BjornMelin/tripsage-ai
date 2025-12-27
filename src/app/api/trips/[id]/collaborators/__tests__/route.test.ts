/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import type { Database } from "@/lib/supabase/database.types";
import { stubRateLimitDisabled, unstubAllEnvs } from "@/test/helpers/env";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";
import { setupUpstashMocks } from "@/test/upstash/redis-mock";
import { GET, POST } from "../route";

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(
      getMockCookiesForTest({
        "sb-access-token": "test-token",
      })
    )
  ),
}));

type TripRow = Pick<Database["public"]["Tables"]["trips"]["Row"], "id" | "user_id">;
type CollaboratorRow = Pick<
  Database["public"]["Tables"]["trip_collaborators"]["Row"],
  "created_at" | "id" | "role" | "trip_id" | "user_id"
>;

const ADMIN_SUPABASE = vi.hoisted(() => ({
  auth: {
    admin: {
      getUserById: vi.fn(),
      inviteUserByEmail: vi.fn(),
    },
  },
  rpc: vi.fn(),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: () => ADMIN_SUPABASE,
}));

const { redis, ratelimit } = setupUpstashMocks();

type SupabaseMockOptions = {
  collaborators?: CollaboratorRow[];
  collaboratorsError?: unknown | null;
  currentUserId?: string | null;
  insertResult?: { data: CollaboratorRow | null; error: unknown | null };
  trip?: TripRow | null;
  tripError?: unknown | null;
};

function createSupabaseMock(opts: SupabaseMockOptions) {
  const tripResult = { data: opts.trip ?? null, error: opts.tripError ?? null };

  const tripsBuilder = {
    eq: vi.fn(() => tripsBuilder),
    maybeSingle: vi.fn(async () => tripResult),
    select: vi.fn(() => tripsBuilder),
  };

  const collaborators = opts.collaborators ?? [];
  const collaboratorsError = opts.collaboratorsError ?? null;
  const insertResult = opts.insertResult ?? {
    data: collaborators[0] ?? null,
    error: null,
  };

  const collabBuilder = {
    delete: vi.fn(() => {
      collabBuilder.operation = "delete";
      return collabBuilder;
    }),
    eq: vi.fn(() => collabBuilder),
    insert: vi.fn((payload: Record<string, unknown>) => {
      collabBuilder.operation = "insert";
      collabBuilder.insertPayload = payload;
      return collabBuilder;
    }),
    insertPayload: {} as Record<string, unknown>,
    operation: "select" as "select" | "insert" | "delete",
    order: vi.fn(() => collabBuilder),
    select: vi.fn(() => collabBuilder),
    single: vi.fn(async () => insertResult),
    // biome-ignore lint/suspicious/noThenProperty: Mock promise-like object for testing
    then(
      onFulfilled: (value: {
        data: CollaboratorRow[];
        error: unknown | null;
      }) => unknown
    ) {
      if (collabBuilder.operation === "select") {
        return Promise.resolve({ data: collaborators, error: collaboratorsError }).then(
          onFulfilled
        );
      }
      return Promise.resolve({ data: [], error: null }).then(onFulfilled);
    },
  };

  return {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: opts.currentUserId ? { id: opts.currentUserId } : null },
        error: opts.currentUserId ? null : { message: "unauthenticated" },
      })),
    },
    from: vi.fn((table: string) => {
      if (table === "trips") return tripsBuilder;
      if (table === "trip_collaborators") return collabBuilder;
      throw new Error(`Unexpected table: ${table}`);
    }),
  };
}

describe("/api/trips/[id]/collaborators", () => {
  beforeEach(() => {
    redis.__reset?.();
    ratelimit.__reset?.();
    stubRateLimitDisabled();
    setRateLimitFactoryForTests(async () => ({
      limit: 60,
      remaining: 59,
      reset: Date.now() + 60_000,
      success: true,
    }));

    ADMIN_SUPABASE.auth.admin.inviteUserByEmail.mockReset();
    ADMIN_SUPABASE.auth.admin.getUserById.mockReset();
    ADMIN_SUPABASE.rpc.mockReset();
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
    unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("returns 400 for invalid trip id", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/abc/collaborators",
    });
    const res = await GET(req, createRouteParamsContext({ id: "abc" }));
    expect(res.status).toBe(400);
  });

  it("returns 404 when trip is not found", async () => {
    const mockSupabase = createSupabaseMock({
      currentUserId: "11111111-1111-4111-8aaa-111111111111",
      trip: null,
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/999/collaborators",
    });
    const res = await GET(req, createRouteParamsContext({ id: "999" }));
    expect(res.status).toBe(404);
  });

  it("lists collaborators and resolves emails for owner", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const collaboratorA = "22222222-2222-4222-8aaa-222222222222";
    const collaboratorB = "33333333-3333-4333-8aaa-333333333333";
    const mockSupabase = createSupabaseMock({
      collaborators: [
        {
          created_at: "2025-01-01T00:00:00.000Z",
          id: 10,
          role: "viewer",
          trip_id: 1,
          user_id: collaboratorA,
        },
        {
          created_at: "2025-01-02T00:00:00.000Z",
          id: 11,
          role: "editor",
          trip_id: 1,
          user_id: collaboratorB,
        },
      ],
      currentUserId: ownerId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    ADMIN_SUPABASE.rpc.mockImplementation(
      (fn: string, args?: Record<string, unknown>) => {
        if (fn !== "auth_user_emails_by_ids") {
          return { data: null, error: null };
        }

        const ids = Array.isArray(args?.p_user_ids) ? args.p_user_ids : [];
        return {
          data: ids.map((id) => ({ email: `${id}@example.com`, user_id: id })),
          error: null,
        };
      }
    );

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/1/collaborators",
    });
    const res = await GET(req, createRouteParamsContext({ id: "1" }));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.isOwner).toBe(true);
    expect(json.ownerId).toBe(ownerId);
    expect(json.collaborators).toHaveLength(2);
    expect(json.collaborators[0].userEmail).toBe(`${collaboratorA}@example.com`);
    expect(json.collaborators[1].userEmail).toBe(`${collaboratorB}@example.com`);
    expect(ADMIN_SUPABASE.rpc).toHaveBeenCalledTimes(1);
    expect(ADMIN_SUPABASE.rpc).toHaveBeenCalledWith("auth_user_emails_by_ids", {
      p_user_ids: [collaboratorA, collaboratorB],
    });
  });

  it("only includes self email when non-owner", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const currentUserId = "22222222-2222-4222-8aaa-222222222222";
    const collaboratorB = "33333333-3333-4333-8aaa-333333333333";
    const mockSupabase = createSupabaseMock({
      collaborators: [
        {
          created_at: "2025-01-01T00:00:00.000Z",
          id: 10,
          role: "viewer",
          trip_id: 1,
          user_id: currentUserId,
        },
        {
          created_at: "2025-01-02T00:00:00.000Z",
          id: 11,
          role: "editor",
          trip_id: 1,
          user_id: collaboratorB,
        },
      ],
      currentUserId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    ADMIN_SUPABASE.rpc.mockImplementation(
      (fn: string, args?: Record<string, unknown>) => {
        if (fn !== "auth_user_emails_by_ids") {
          return { data: null, error: null };
        }

        const ids = Array.isArray(args?.p_user_ids) ? args.p_user_ids : [];
        return {
          data: ids.map((id) => ({
            email: id === currentUserId ? "user-a@example.com" : null,
            user_id: id,
          })),
          error: null,
        };
      }
    );

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/1/collaborators",
    });
    const res = await GET(req, createRouteParamsContext({ id: "1" }));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.isOwner).toBe(false);
    expect(json.collaborators[0].userEmail).toBe("user-a@example.com");
    expect(json.collaborators[1].userEmail).toBeUndefined();
    expect(ADMIN_SUPABASE.rpc).toHaveBeenCalledTimes(1);
    expect(ADMIN_SUPABASE.rpc).toHaveBeenCalledWith("auth_user_emails_by_ids", {
      p_user_ids: [currentUserId],
    });
  });

  it("prevents non-owners from inviting collaborators", async () => {
    const collaboratorId = "22222222-2222-4222-8aaa-222222222222";
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const mockSupabase = createSupabaseMock({
      currentUserId: collaboratorId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      body: { email: "new@example.com", role: "viewer" },
      method: "POST",
      url: "http://localhost/api/trips/1/collaborators",
    });
    const res = await POST(req, createRouteParamsContext({ id: "1" }));
    expect(res.status).toBe(403);
  });

  it("validates invite payload", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      body: { email: "not-an-email", role: "viewer" },
      method: "POST",
      url: "http://localhost/api/trips/1/collaborators",
    });
    const res = await POST(req, createRouteParamsContext({ id: "1" }));
    expect(res.status).toBe(400);
  });

  it("adds existing user as collaborator without sending invite", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const existingUserId = "22222222-2222-4222-8aaa-222222222222";

    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      insertResult: {
        data: {
          created_at: "2025-01-01T00:00:00.000Z",
          id: 99,
          role: "viewer",
          trip_id: 1,
          user_id: existingUserId,
        },
        error: null,
      },
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    ADMIN_SUPABASE.rpc.mockResolvedValue({ data: existingUserId, error: null });

    const req = createMockNextRequest({
      body: { email: "existing@example.com", role: "viewer" },
      method: "POST",
      url: "http://localhost/api/trips/1/collaborators",
    });
    const res = await POST(req, createRouteParamsContext({ id: "1" }));
    const json = await res.json();

    expect(res.status).toBe(201);
    expect(json.invited).toBe(false);
    expect(json.collaborator.userId).toBe(existingUserId);
    expect(ADMIN_SUPABASE.auth.admin.inviteUserByEmail).not.toHaveBeenCalled();
  });

  it("invites missing user and adds them as collaborator", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const invitedUserId = "33333333-3333-4333-8aaa-333333333333";

    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      insertResult: {
        data: {
          created_at: "2025-01-01T00:00:00.000Z",
          id: 99,
          role: "editor",
          trip_id: 1,
          user_id: invitedUserId,
        },
        error: null,
      },
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    ADMIN_SUPABASE.rpc.mockResolvedValue({ data: null, error: null });
    ADMIN_SUPABASE.auth.admin.inviteUserByEmail.mockResolvedValue({
      data: { user: { id: invitedUserId } },
      error: null,
    });

    const req = createMockNextRequest({
      body: { email: "new@example.com", role: "editor" },
      method: "POST",
      url: "http://localhost/api/trips/1/collaborators",
    });
    const res = await POST(req, createRouteParamsContext({ id: "1" }));
    const json = await res.json();

    expect(res.status).toBe(201);
    expect(json.invited).toBe(true);
    expect(json.collaborator.userId).toBe(invitedUserId);
    expect(ADMIN_SUPABASE.auth.admin.inviteUserByEmail).toHaveBeenCalledTimes(1);
  });
});
