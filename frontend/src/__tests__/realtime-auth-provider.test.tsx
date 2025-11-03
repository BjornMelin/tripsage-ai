/**
 * @fileoverview Tests for RealtimeAuthProvider token lifecycle.
 * Verifies that setAuth is called with token on login and cleared on logout/unmount.
 */

import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import { RealtimeAuthProvider } from "@/components/providers/realtime-auth-provider";

vi.mock("@/lib/supabase/client", () => {
  const setAuth = vi.fn();
  const onAuthStateChange = vi.fn(
    (_event: AuthChangeEvent, _session: Session | null) => ({
      data: { subscription: { unsubscribe: vi.fn() } },
    })
  );
  return {
    getBrowserClient: () => ({ auth: { onAuthStateChange }, realtime: { setAuth } }),
  };
});

describe("RealtimeAuthProvider", () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.clearAllMocks();
  });

  it("sets auth on login", async () => {
    const { getBrowserClient } = await import("@/lib/supabase/client");
    const client = getBrowserClient();
    render(<RealtimeAuthProvider />);

    const token = "abc";
    // Simulate login event
    (client.auth.onAuthStateChange as any).mock.calls[0][0]("SIGNED_IN", {
      access_token: token,
      expires_in: 3600,
      refresh_token: "refresh",
      token_type: "bearer",
      user: { id: "user-id" },
    } as unknown as Session);
    expect(client.realtime.setAuth).toHaveBeenCalledWith(token);
  });

  it("clears auth on logout and on unmount", async () => {
    const { getBrowserClient } = await import("@/lib/supabase/client");
    const client = getBrowserClient();
    const { unmount } = render(<RealtimeAuthProvider />);

    // Simulate logout
    (client.auth.onAuthStateChange as any).mock.calls[0][0]("SIGNED_OUT", null);
    expect(client.realtime.setAuth).toHaveBeenCalledWith("");

    // Unmount clears again
    unmount();
    expect(client.realtime.setAuth).toHaveBeenCalledWith("");
  });
});
