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

const mockedFetchApi = vi.mocked(fetchApi);
let auth: SupabaseAuthMock;
let testUser: User;

const createTestUser = (): User => ({
  id: "test-user-id",
  app_metadata: {},
  user_metadata: {},
  aud: "authenticated",
  email: "test@example.com",
  created_at: new Date(0).toISOString(),
});

const createTestSession = (accessToken: string, user: User): Session => ({
  access_token: accessToken,
  refresh_token: `${accessToken}-refresh`,
  expires_in: 3_600,
  token_type: "bearer",
  user,
});

const buildGetSessionResponse = (session: Session | null) =>
  session
    ? { data: { session }, error: null }
    : { data: { session: null }, error: null };

const buildRefreshResponse = (session: Session | null, user: User | null) => ({
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

  return <button onClick={call}>{result}</button>;
}

describe("useAuthenticatedApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const supabase = createClient();
    auth = supabase.auth as unknown as SupabaseAuthMock;
    testUser = createTestUser();
    Object.values(auth).forEach((fn) => {
      if (typeof fn === "function" && "mockReset" in fn) {
        (fn as ReturnType<typeof vi.fn>).mockReset();
      }
    });
    mockedFetchApi.mockResolvedValue({ ok: true } as unknown as Response);
    auth.getSession.mockResolvedValue(buildGetSessionResponse(null));
    auth.refreshSession.mockResolvedValue(buildRefreshResponse(null, null));
    auth.signOut.mockResolvedValue({ error: null });
  });

  it("throws 401 when the session is missing and refresh fails", async () => {
    render(<TestCaller />);

    await userEvent.click(screen.getByRole("button", { name: "ready" }));

    expect(screen.getByRole("button", { name: "UNAUTHORIZED" })).toBeInTheDocument();
  });

  it("attaches Authorization header when a session exists", async () => {
    const session = createTestSession("tok", testUser);
    auth.getSession.mockResolvedValue(buildGetSessionResponse(session));

    render(<TestCaller />);

    await userEvent.click(screen.getByRole("button", { name: "ready" }));

    expect(mockedFetchApi).toHaveBeenCalledTimes(1);
    const [, options] = mockedFetchApi.mock.calls[0];
    expect(options?.auth).toBe("Bearer tok");
  });

  it("refreshes on 401 and retries once", async () => {
    mockedFetchApi
      .mockRejectedValueOnce(
        new ApiError({ message: "401", status: 401, code: "UNAUTHORIZED" })
      )
      .mockResolvedValueOnce({ ok: true });

    const staleSession = createTestSession("stale", testUser);
    const freshUser = createTestUser();
    const refreshedSession = createTestSession("fresh", freshUser);

    auth.getSession.mockResolvedValue(buildGetSessionResponse(staleSession));
    auth.refreshSession.mockResolvedValue(
      buildRefreshResponse(refreshedSession, refreshedSession.user)
    );

    render(<TestCaller />);

    await userEvent.click(screen.getByRole("button", { name: "ready" }));

    expect(mockedFetchApi).toHaveBeenCalledTimes(2);
    const [, retryOptions] = mockedFetchApi.mock.calls[1];
    expect(retryOptions?.auth).toBe("Bearer fresh");
  });
});
