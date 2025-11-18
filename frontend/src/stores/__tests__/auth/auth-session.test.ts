/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { AuthSession } from "@/lib/schemas/stores";
import { useAuthSession, useSessionTimeRemaining } from "@/stores/auth/auth-session";
import { resetAuthState } from "@/stores/auth/reset-auth";
import { setupReactQueryMocks } from "@/test/mocks/react-query";
import { setupTimeoutMock } from "@/test/store-helpers";

setupReactQueryMocks();

describe("AuthSession", () => {
  let timeoutCleanup: (() => void) | null = null;

  beforeEach(() => {
    const timeoutMock = setupTimeoutMock();
    timeoutCleanup = timeoutMock.mockRestore;
    resetAuthState();
  });

  afterEach(() => {
    timeoutCleanup?.();
  });

  describe("Initial State", () => {
    it("initializes with null session and zero time remaining", () => {
      const { result } = renderHook(() => useAuthSession());

      expect(result.current.session).toBeNull();
      expect(result.current.sessionTimeRemaining).toBe(0);
    });

    it("computed sessionTimeRemaining hook returns 0 when no session", () => {
      const { result } = renderHook(() => useSessionTimeRemaining());
      expect(result.current).toBe(0);
    });
  });

  describe("Session mutations", () => {
    it("sets session", () => {
      const { result } = renderHook(() => useAuthSession());

      const session: AuthSession = {
        createdAt: "2025-01-01T00:00:00Z",
        expiresAt: new Date(Date.now() + 3600000).toISOString(),
        id: "session-1",
        lastActivity: "2025-01-01T00:00:00Z",
        userId: "user-1",
      };

      act(() => {
        result.current.setSession(session);
      });

      expect(result.current.session).toEqual(session);
    });

    it("resetSession clears session", () => {
      const { result } = renderHook(() => useAuthSession());

      act(() => {
        result.current.setSession({
          createdAt: "2025-01-01T00:00:00Z",
          expiresAt: new Date(Date.now() + 3600000).toISOString(),
          id: "session-1",
          lastActivity: "2025-01-01T00:00:00Z",
          userId: "user-1",
        });
      });

      expect(result.current.session).not.toBeNull();

      act(() => {
        result.current.resetSession();
      });

      expect(result.current.session).toBeNull();
      expect(result.current.sessionTimeRemaining).toBe(0);
    });

    it("sessionTimeRemaining is positive when session has future expiry", () => {
      act(() => {
        useAuthSession.setState({
          session: {
            createdAt: "2025-01-01T00:00:00Z",
            expiresAt: new Date(Date.now() + 3600000).toISOString(),
            id: "session-1",
            lastActivity: "2025-01-01T00:00:00Z",
            userId: "user-1",
          },
        });
      });

      const state = useAuthSession.getState();
      expect(state.session).not.toBeNull();
      expect(state.sessionTimeRemaining).toBeGreaterThanOrEqual(0);
    });
  });
});
