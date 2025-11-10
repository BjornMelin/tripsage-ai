import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RealtimeAuthProvider } from "@/components/providers/realtime-auth-provider";

/** Mock setAuth function for testing */
const mockSetAuth = vi.fn();

/** Mock onAuthStateChange function for testing */
const mockOnAuthStateChange = vi
  .fn()
  .mockImplementation((_event: AuthChangeEvent, _session: Session | null) => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  }));

vi.mock("@/lib/supabase/client", () => ({
  getBrowserClient: () => ({
    auth: { onAuthStateChange: mockOnAuthStateChange },
    realtime: { setAuth: mockSetAuth },
  }),
}));

describe("RealtimeAuthProvider", () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
    vi.clearAllMocks();
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("sets auth on login", async () => {
    const { getBrowserClient } = await import("@/lib/supabase/client");
    getBrowserClient();
    render(<RealtimeAuthProvider />);

    const token = "abc";
    // Simulate login event
    const authCallback = mockOnAuthStateChange.mock.calls[0][0];
    authCallback("SIGNED_IN", {
      access_token: token,
      expiresIn: 3600,
      refreshToken: "refresh",
      tokenType: "bearer",
      user: { id: "user-id" },
    } as unknown as Session);
    expect(mockSetAuth).toHaveBeenCalledWith(token);
  });

  it("clears auth on logout and on unmount", async () => {
    const { getBrowserClient } = await import("@/lib/supabase/client");
    getBrowserClient();
    const { unmount } = render(<RealtimeAuthProvider />);

    // Simulate logout
    const authCallback = mockOnAuthStateChange.mock.calls[0][0];
    authCallback("SIGNED_OUT", null);
    expect(mockSetAuth).toHaveBeenCalledWith("");

    // Unmount clears again
    unmount();
    expect(mockSetAuth).toHaveBeenCalledWith("");
  });
});
