/**
 * @fileoverview Tests for the useAuthenticatedApi hook.
 */

import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/test-utils";

vi.mock("@/lib/api/client", () => ({
  fetchApi: vi.fn(async (_endpoint: string, _opts: any) => ({ ok: true })),
}));

// Local helper component to drive the hook
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";

/**
 * Test component to drive the useAuthenticatedApi hook.
 * @param endpoint The API endpoint to call.
 * @return JSX element with a button to trigger the API call.
 */
function TestCaller({ endpoint = "/api/ping" }: { endpoint?: string }) {
  const { authenticatedApi } = useAuthenticatedApi();
  const [result, setResult] = React.useState<string>("");
  const call = async () => {
    try {
      const res = await authenticatedApi.get<any>(endpoint);
      setResult(JSON.stringify(res));
    } catch (e) {
      setResult((e as any).code || "ERR");
    }
  };
  return (
    <button onClick={call} aria-label="call">
      {result || "ready"}
    </button>
  );
}

describe("useAuthenticatedApi", () => {
  let fetchApi: any;

  beforeEach(async () => {
    vi.resetAllMocks();
    fetchApi = (await import("@/lib/api/client")).fetchApi as any;
  });

  it("throws 401 when no session and no refresh", async () => {
    vi.doMock("@/lib/supabase/client", () => ({
      createClient: () => ({
        auth: {
          getSession: vi.fn(async () => ({ data: { session: null } })),
          refreshSession: vi.fn(async () => ({ data: { session: null } })),
          signOut: vi.fn(async () => undefined),
        },
      }),
    }));
    render(<TestCaller />);
    const userEvent = (await import("@testing-library/user-event")).default;
    await userEvent.click(screen.getByRole("button", { name: "call" }));
    expect(screen.getByRole("button", { name: "UNAUTHORIZED" })).toBeInTheDocument();
  });

  it("attaches Authorization header when session exists", async () => {
    const getSession = vi.fn(async () => ({
      data: { session: { access_token: "tok" } },
    }));
    vi.doMock("@/lib/supabase/client", () => ({
      createClient: () => ({ auth: { getSession, refreshSession: vi.fn() } }),
    }));

    render(<TestCaller />);
    await screen.findByRole("button", { name: "ready" });
    await (await import("@testing-library/user-event")).default.click(
      screen.getByRole("button", { name: "ready" })
    );
    expect(fetchApi).toHaveBeenCalled();
    const [, opts] = fetchApi.mock.calls[0];
    expect(opts.auth).toBe("Bearer tok");
  });

  it("refreshes on 401 and retries once", async () => {
    // First call will throw ApiError(401), then succeed
    const { ApiError } = await import("@/lib/api/error-types");
    (fetchApi as any)
      .mockRejectedValueOnce(
        new ApiError({ message: "401", status: 401, code: "UNAUTHORIZED" })
      )
      .mockResolvedValueOnce({ ok: true });
    const getSession = vi.fn(async () => ({
      data: { session: { access_token: "stale" } },
    }));
    const refreshSession = vi.fn(async () => ({
      data: { session: { access_token: "fresh" } },
    }));
    vi.doMock("@/lib/supabase/client", () => ({
      createClient: () => ({ auth: { getSession, refreshSession, signOut: vi.fn() } }),
    }));

    render(<TestCaller />);
    const userEvent = (await import("@testing-library/user-event")).default;
    await userEvent.click(screen.getByRole("button", { name: "ready" }));
    expect(fetchApi).toHaveBeenCalledTimes(2);
  });
});
