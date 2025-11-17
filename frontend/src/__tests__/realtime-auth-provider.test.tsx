/** @vitest-environment jsdom */

import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RealtimeAuthProvider } from "@/components/providers/realtime-auth-provider";
import { render } from "@/test/test-utils";

/** Mock setAuth function for testing */
const mockSetAuth = vi.fn();

/** Mock getSession function for testing */
const mockGetSession = vi.fn().mockResolvedValue({
  data: {
    session: {
      access_token: "initial-token",
      user: { id: "user-id" },
    },
  },
  error: null,
});

/** Mock onAuthStateChange function for testing */
const mockOnAuthStateChange = vi
  .fn()
  .mockImplementation((_event: AuthChangeEvent, _session: Session | null) => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  }));

vi.mock("@/lib/supabase", () => ({
  getBrowserClient: () => ({
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
    },
    realtime: { setAuth: mockSetAuth },
  }),
}));

describe("RealtimeAuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("sets auth on login", async () => {
    render(<RealtimeAuthProvider />);

    // Wait for initial effect to run
    await vi.waitFor(() => {
      expect(mockSetAuth).toHaveBeenCalledWith("initial-token");
    });

    const token = "abc";
    // Simulate login event via auth state change callback
    const authCallback = mockOnAuthStateChange.mock.calls[0]?.[0];
    if (authCallback) {
      authCallback("SIGNED_IN", {
        access_token: token,
        expiresIn: 3600,
        refreshToken: "refresh",
        tokenType: "bearer",
        user: { id: "user-id" },
      } as unknown as Session);
    }

    await vi.waitFor(() => {
      expect(mockSetAuth).toHaveBeenCalledWith(token);
    });
  });

  it("clears auth on logout and on unmount", async () => {
    const { unmount } = render(<RealtimeAuthProvider />);

    // Wait for initial effect
    await vi.waitFor(() => {
      expect(mockSetAuth).toHaveBeenCalledWith("initial-token");
    });

    // Get the callback before clearing mocks
    const authCallback = mockOnAuthStateChange.mock.calls[0]?.[0];
    expect(authCallback).toBeDefined();

    // Clear call history but keep mock implementation
    mockSetAuth.mockClear();

    // Simulate logout
    if (authCallback) {
      authCallback("SIGNED_OUT", null);
    }

    await vi.waitFor(() => {
      expect(mockSetAuth).toHaveBeenCalledWith("");
    });

    // Clear call history again
    mockSetAuth.mockClear();

    // Unmount clears again (cleanup runs synchronously)
    unmount();

    // Unmount cleanup should call setAuth("") immediately
    expect(mockSetAuth).toHaveBeenCalledWith("");
  });
});
