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
import { DELETE, PATCH } from "../route";

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

const { redis, ratelimit } = setupUpstashMocks();

type SupabaseMockOptions = {
  currentUserId?: string | null;
  deleteResult?: { count: number; error: unknown | null };
  trip?: TripRow | null;
  tripError?: unknown | null;
  updateResult?: { data: CollaboratorRow | null; error: unknown | null };
};

function createSupabaseMock(opts: SupabaseMockOptions) {
  const tripResult = { data: opts.trip ?? null, error: opts.tripError ?? null };

  const tripsBuilder = {
    eq: vi.fn(() => tripsBuilder),
    maybeSingle: vi.fn(() => tripResult),
    select: vi.fn(() => tripsBuilder),
  };

  const updateResult = opts.updateResult ?? { data: null, error: null };
  const deleteResult = opts.deleteResult ?? { count: 1, error: null };

  const collabBuilder = {
    delete() {
      this.operation = "delete";
      return this;
    },
    eq() {
      return this;
    },
    maybeSingle: vi.fn(() => {
      if (collabBuilder.operation === "update") return updateResult;
      return { data: null, error: null };
    }),
    operation: "select" as "select" | "update" | "delete",
    select() {
      return this;
    },
    // biome-ignore lint/suspicious/noThenProperty: Mock promise-like object for testing
    then(onFulfilled: (value: { count: number; error: unknown | null }) => unknown) {
      if (this.operation === "delete") {
        return Promise.resolve(deleteResult).then(onFulfilled);
      }
      return Promise.resolve({ count: 0, error: null }).then(onFulfilled);
    },
    update(payload: Record<string, unknown>) {
      this.operation = "update";
      this.updatePayload = payload;
      return this;
    },
    updatePayload: {} as Record<string, unknown>,
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

describe("/api/trips/[id]/collaborators/[userId]", () => {
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
      body: { role: "viewer" },
      method: "PATCH",
      url: "http://localhost/api/trips/abc/collaborators/user",
    });
    const res = await PATCH(
      req,
      createRouteParamsContext({ id: "abc", userId: ownerId })
    );
    expect(res.status).toBe(400);
  });

  it("returns 400 for invalid collaborator userId on PATCH", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      body: { role: "viewer" },
      method: "PATCH",
      url: "http://localhost/api/trips/1/collaborators/not-a-uuid",
    });
    const res = await PATCH(
      req,
      createRouteParamsContext({ id: "1", userId: "not-a-uuid" })
    );
    expect(res.status).toBe(400);
  });

  it("returns 404 when trip is not found", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      trip: null,
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      body: { role: "viewer" },
      method: "PATCH",
      url: "http://localhost/api/trips/999/collaborators/user",
    });
    const res = await PATCH(
      req,
      createRouteParamsContext({ id: "999", userId: ownerId })
    );
    expect(res.status).toBe(404);
  });

  it("prevents non-owners from updating collaborator roles", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const collaboratorId = "22222222-2222-4222-8aaa-222222222222";
    const mockSupabase = createSupabaseMock({
      currentUserId: collaboratorId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      body: { role: "editor" },
      method: "PATCH",
      url: "http://localhost/api/trips/1/collaborators/user",
    });
    const res = await PATCH(
      req,
      createRouteParamsContext({ id: "1", userId: collaboratorId })
    );
    expect(res.status).toBe(403);
  });

  it("updates collaborator role for owner", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const collaboratorId = "22222222-2222-4222-8aaa-222222222222";
    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      trip: { id: 1, user_id: ownerId },
      updateResult: {
        data: {
          created_at: "2025-01-01T00:00:00.000Z",
          id: 100,
          role: "admin",
          trip_id: 1,
          user_id: collaboratorId,
        },
        error: null,
      },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      body: { role: "admin" },
      method: "PATCH",
      url: "http://localhost/api/trips/1/collaborators/user",
    });
    const res = await PATCH(
      req,
      createRouteParamsContext({ id: "1", userId: collaboratorId })
    );
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.collaborator.userId).toBe(collaboratorId);
    expect(json.collaborator.role).toBe("admin");
  });

  it("allows collaborator to leave the trip", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const collaboratorId = "22222222-2222-4222-8aaa-222222222222";
    const mockSupabase = createSupabaseMock({
      currentUserId: collaboratorId,
      deleteResult: { count: 1, error: null },
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/trips/1/collaborators/user",
    });
    const res = await DELETE(
      req,
      createRouteParamsContext({ id: "1", userId: collaboratorId })
    );
    expect(res.status).toBe(204);
  });

  it("returns 400 for invalid collaborator userId on DELETE", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/trips/1/collaborators/not-a-uuid",
    });
    const res = await DELETE(
      req,
      createRouteParamsContext({ id: "1", userId: "not-a-uuid" })
    );
    expect(res.status).toBe(400);
  });

  it("prevents removing other collaborators when not owner", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const currentUserId = "22222222-2222-4222-8aaa-222222222222";
    const otherUserId = "33333333-3333-4333-8aaa-333333333333";
    const mockSupabase = createSupabaseMock({
      currentUserId,
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/trips/1/collaborators/user",
    });
    const res = await DELETE(
      req,
      createRouteParamsContext({ id: "1", userId: otherUserId })
    );
    expect(res.status).toBe(403);
  });

  it("returns 404 when collaborator removal affects no rows", async () => {
    const ownerId = "11111111-1111-4111-8aaa-111111111111";
    const collaboratorId = "22222222-2222-4222-8aaa-222222222222";
    const mockSupabase = createSupabaseMock({
      currentUserId: ownerId,
      deleteResult: { count: 0, error: null },
      trip: { id: 1, user_id: ownerId },
    });
    setSupabaseFactoryForTests(() => Promise.resolve(mockSupabase as never));

    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/trips/1/collaborators/user",
    });
    const res = await DELETE(
      req,
      createRouteParamsContext({ id: "1", userId: collaboratorId })
    );
    expect(res.status).toBe(404);
  });
});
