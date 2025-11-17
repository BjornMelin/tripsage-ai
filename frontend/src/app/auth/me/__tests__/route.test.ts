/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest } from "@/test/route-helpers";

const GET_OPTIONAL_USER_MOCK = vi.hoisted(
  () =>
    vi.fn(
      async () =>
        ({ supabase: {}, user: null }) as {
          supabase: unknown;
          user: unknown | null;
        }
    ) as MockInstance<() => Promise<{ supabase: unknown; user: unknown | null }>>
);

const MAP_USER_MOCK = vi.hoisted(
  () => vi.fn((user: unknown) => user) as MockInstance<(user: unknown) => unknown>
);

vi.mock("@/lib/auth/server", () => ({
  getOptionalUser: GET_OPTIONAL_USER_MOCK,
  mapSupabaseUserToAuthUser: MAP_USER_MOCK,
}));

import { GET } from "../route";

describe("auth/me route", () => {
  beforeEach(() => {
    GET_OPTIONAL_USER_MOCK.mockClear();
    MAP_USER_MOCK.mockClear();
  });

  it("returns 401 with user: null when unauthenticated", async () => {
    GET_OPTIONAL_USER_MOCK.mockResolvedValueOnce({ supabase: {}, user: null });

    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/me",
    });

    const res = await GET(req);

    expect(GET_OPTIONAL_USER_MOCK).toHaveBeenCalledTimes(1);
    expect(MAP_USER_MOCK).not.toHaveBeenCalled();
    expect(res.status).toBe(401);
    const body = (await res.json()) as { user: unknown | null };
    expect(body.user).toBeNull();
  });

  it("maps Supabase user to AuthUser and returns 200 with user payload when authenticated", async () => {
    const supabaseUser = { email: "user@example.com", id: "user-123" };
    const mappedUser = {
      displayName: "User",
      email: "user@example.com",
      id: "user-123",
    };

    GET_OPTIONAL_USER_MOCK.mockResolvedValueOnce({
      supabase: {},
      user: supabaseUser,
    });
    MAP_USER_MOCK.mockImplementationOnce((user) => {
      expect(user).toEqual(supabaseUser);
      return mappedUser;
    });

    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/me",
    });

    const res = await GET(req);

    expect(GET_OPTIONAL_USER_MOCK).toHaveBeenCalledTimes(1);
    expect(MAP_USER_MOCK).toHaveBeenCalledTimes(1);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { user: unknown | null };
    expect(body.user).toEqual(mappedUser);
  });
});
