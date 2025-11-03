/**
 * @fileoverview Tests for the useAuthenticatedApi hook with Supabase session handling.
 */

import type { Session, User } from "@supabase/supabase-js";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { fetchApi } from "@/lib/api/client";
import { ApiError } from "@/lib/api/error-types";
import { createClient } from "@/lib/supabase/client";
import type { SupabaseAuthMock } from "@/test/mock-helpers";
import { render, screen } from "@/test/test-utils";

vi.mock("@/lib/api/client", () => ({
  fetchApi: vi.fn(),
}));

const MOCKED_FETCH_API = vi.mocked(fetchApi);
let auth: SupabaseAuthMock;
let testUser: User;

const CREATE_TEST_USER = (): User => ({
  app_metadata: {},
  aud: "authenticated",
  created_at: new Date(0).toISOString(),
  email: "test@example.com",
  id: "test-user-id",
  user_metadata: {},
});

const CREATE_TEST_SESSION = (accessToken: string, user: User): Session => ({
  access_token: accessToken,
  expires_in: 3_600,
  refresh_token: `${accessToken}-refresh`,
  token_type: "bearer",
  user,
});

const BUILD_GET_SESSION_RESPONSE = (session: Session | null) =>
  session
    ? { data: { session }, error: null }
    : { data: { session: null }, error: null };

const BUILD_REFRESH_RESPONSE = (session: Session | null, user: User | null) => ({
  data: { session, user },
  error: null,
});

function TestCaller({ endpoint = "/api/ping" }: { endpoint?: string }) {
  const { authenticatedApi } = useAuthenticatedApi();
  const [result, setResult] = useState<string>("ready");

  const call = async () => {
    try {
      await authenticatedApi.get(endpoint);
      setResult("ok");
    } catch (error) {
      if (error instanceof ApiError) {
        setResult(error.code ?? "ERR");
        return;
      }
      setResult("ERR");
    }
  };

  return (
    <button type="button" onClick={call}>
      {result}
    </button>
  );
}

describe("useAuthenticatedApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const supabase = createClient();
    auth = supabase.auth as unknown as SupabaseAuthMock;
    testUser = CREATE_TEST_USER();
    Object.values(auth).forEach((fn) => {
      if (typeof fn === "function" && "mockReset" in fn) {
        (fn as ReturnType<typeof vi.fn>).mockReset();
      }
    });
    MOCKED_FETCH_API.mockResolvedValue({ ok: true } as unknown as Response);
    auth.getSession.mockResolvedValue(BUILD_GET_SESSION_RESPONSE(null));
    auth.refreshSession.mockResolvedValue(BUILD_REFRESH_RESPONSE(null, null));
    auth.signOut.mockResolvedValue({ error: null });
  });

  it("throws 401 when the session is missing and refresh fails", async () => {
    render(<TestCaller />);

    await userEvent.click(screen.getByRole("button", { name: "ready" }));

    expect(screen.getByRole("button", { name: "UNAUTHORIZED" })).toBeInTheDocument();
  });

  it("attaches Authorization header when a session exists", async () => {
    const session = CREATE_TEST_SESSION("tok", testUser);
    auth.getSession.mockResolvedValue(BUILD_GET_SESSION_RESPONSE(session));

    render(<TestCaller />);

    await userEvent.click(screen.getByRole("button", { name: "ready" }));

    expect(MOCKED_FETCH_API).toHaveBeenCalledTimes(1);
    const [, options] = MOCKED_FETCH_API.mock.calls[0];
    expect(options?.auth).toBe("Bearer tok");
  });

  it("refreshes on 401 and retries once", async () => {
    MOCKED_FETCH_API.mockRejectedValueOnce(
      new ApiError({ code: "UNAUTHORIZED", message: "401", status: 401 })
    ).mockResolvedValueOnce({ ok: true });

    const staleSession = CREATE_TEST_SESSION("stale", testUser);
    const freshUser = CREATE_TEST_USER();
    const refreshedSession = CREATE_TEST_SESSION("fresh", freshUser);

    auth.getSession.mockResolvedValue(BUILD_GET_SESSION_RESPONSE(staleSession));
    auth.refreshSession.mockResolvedValue(
      BUILD_REFRESH_RESPONSE(refreshedSession, refreshedSession.user)
    );

    render(<TestCaller />);

    await userEvent.click(screen.getByRole("button", { name: "ready" }));

    expect(MOCKED_FETCH_API).toHaveBeenCalledTimes(2);
    const [, retryOptions] = MOCKED_FETCH_API.mock.calls[1];
    expect(retryOptions?.auth).toBe("Bearer fresh");
  });
});
