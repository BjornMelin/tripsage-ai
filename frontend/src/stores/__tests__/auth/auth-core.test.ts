/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthCore } from "@/stores/auth/auth-core";
import { useAuthSession } from "@/stores/auth/auth-session";
import { useAuthValidation } from "@/stores/auth/auth-validation";
import { resetAuthState } from "@/stores/auth/reset-auth";
import { createMockUser } from "@/test/factories";
import { setupTimeoutMock } from "@/test/store-helpers";

// Mock fetch for API calls
global.fetch = vi.fn();

describe("AuthCore", () => {
  let timeoutCleanup: (() => void) | null = null;

  beforeEach(() => {
    const timeoutMock = setupTimeoutMock();
    timeoutCleanup = timeoutMock.mockRestore;
    resetAuthState();
    vi.clearAllMocks();
  });

  afterEach(() => {
    timeoutCleanup?.();
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useAuthCore());

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isLoggingIn).toBe(false);
      expect(result.current.isRegistering).toBe(false);
    });

    it("computed properties work correctly with empty state", () => {
      const { result } = renderHook(() => useAuthCore());

      expect(result.current.userDisplayName).toBe("");
    });
  });

  // Login and registration flows are handled by Supabase SSR /auth routes with HTML forms.
  // auth-core remains a view-model over the current user snapshot and initialization/logout flows.

  describe("Logout", () => {
    it("successfully logs out and clears auth state", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      // Set up authenticated state
      act(() => {
        useAuthCore.setState({
          isAuthenticated: true,
          user: createMockUser(),
        });
      });

      expect(result.current.isAuthenticated).toBe(true);

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBeNull();
    });

    it("clears persisted auth session data", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      act(() => {
        useAuthCore.setState({
          isAuthenticated: true,
          user: createMockUser(),
        });

        useAuthSession.setState({
          session: {
            createdAt: "2025-01-01T00:00:00Z",
            expiresAt: "2025-01-02T00:00:00Z",
            id: "session-1",
            lastActivity: "2025-01-01T01:00:00Z",
            userId: "user-1",
          },
        });
      });

      await act(async () => {
        await result.current.logout();
      });

      const authSessionState = useAuthSession.getState();
      expect(authSessionState.session).toBeNull();
    });

    it("invokes auth-session resetSession when logging out", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const sessionState = useAuthSession.getState();
      const resetSessionSpy = vi.spyOn(sessionState, "resetSession");

      const { result } = renderHook(() => useAuthCore());

      await act(async () => {
        await result.current.logout();
      });

      expect(resetSessionSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("Utility Actions", () => {
    it("sets user directly", () => {
      const { result } = renderHook(() => useAuthCore());

      const user = createMockUser({ id: "user-1" });

      act(() => {
        result.current.setUser(user);
      });

      expect(result.current.user).toEqual(user);

      act(() => {
        result.current.setUser(null);
      });

      expect(result.current.user).toBeNull();
    });

    it("clears error", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        useAuthCore.setState({ error: "Test error" });
      });

      expect(result.current.error).toBe("Test error");

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it("initializes with valid session", async () => {
      const mockUser = createMockUser();
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ user: mockUser }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      await act(async () => {
        await result.current.initialize();
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
    });

    it("initializes with invalid session clears state", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      await act(async () => {
        await result.current.initialize();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });
  });

  describe("User Display Name", () => {
    it("uses displayName when available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(createMockUser({ displayName: "Custom Name" }));
      });

      expect(result.current.userDisplayName).toBe("Custom Name");
    });

    it("uses firstName + lastName when displayName not available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(
          createMockUser({ displayName: undefined, firstName: "John", lastName: "Doe" })
        );
      });

      expect(result.current.userDisplayName).toBe("John Doe");
    });

    it("uses firstName when lastName not available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(
          createMockUser({
            displayName: undefined,
            firstName: "Jane",
            lastName: undefined,
          })
        );
      });

      expect(result.current.userDisplayName).toBe("Jane");
    });

    it("uses email prefix when no names available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(
          createMockUser({
            displayName: undefined,
            email: "username@example.com",
            firstName: undefined,
            lastName: undefined,
          })
        );
      });

      expect(result.current.userDisplayName).toBe("username");
    });
  });

  describe("Auth reset orchestration", () => {
    it("resetAuthState clears auth-core, session, and validation slices", () => {
      const mockUser = createMockUser();

      act(() => {
        useAuthCore.setState({
          error: "Some error",
          isAuthenticated: true,
          isLoading: true,
          isLoggingIn: true,
          isRegistering: true,
          user: mockUser,
          userDisplayName: "Display Name",
        });

        useAuthSession.setState({
          session: {
            createdAt: "2025-01-01T00:00:00Z",
            expiresAt: "2025-01-02T00:00:00Z",
            id: "session-1",
            lastActivity: "2025-01-01T01:00:00Z",
            userId: "user-1",
          },
        });

        useAuthValidation.setState({
          isResettingPassword: true,
          isVerifyingEmail: true,
          passwordResetError: "Reset error",
          registerError: "Register error",
        });
      });

      act(() => {
        resetAuthState();
      });

      const coreState = useAuthCore.getState();
      const sessionState = useAuthSession.getState();
      const validationState = useAuthValidation.getState();

      expect(coreState.isAuthenticated).toBe(false);
      expect(coreState.user).toBeNull();
      expect(coreState.error).toBeNull();
      expect(coreState.isLoading).toBe(false);
      expect(coreState.isLoggingIn).toBe(false);
      expect(coreState.isRegistering).toBe(false);
      expect(coreState.userDisplayName).toBe("");

      expect(sessionState.session).toBeNull();

      expect(validationState.isResettingPassword).toBe(false);
      expect(validationState.isVerifyingEmail).toBe(false);
      expect(validationState.passwordResetError).toBeNull();
      expect(validationState.registerError).toBeNull();
    });
  });
});
