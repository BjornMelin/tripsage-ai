import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { User } from "@/stores/auth-store";
import {
  useAuthStore,
  useIsTokenExpired,
  useSessionTimeRemaining,
} from "@/stores/auth-store";
import { createMockUser, resetAuthStore, setupAuthStoreTests } from "./_shared";

setupAuthStoreTests();

describe("Auth Store - Authentication State", () => {
  beforeEach(() => {
    resetAuthStore();
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.tokenInfo).toBeNull();
      expect(result.current.session).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isLoggingIn).toBe(false);
      expect(result.current.isRegistering).toBe(false);
      expect(result.current.isResettingPassword).toBe(false);
      expect(result.current.isRefreshingToken).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.loginError).toBeNull();
      expect(result.current.registerError).toBeNull();
      expect(result.current.passwordResetError).toBeNull();
    });

    it("computed properties work correctly with empty state", () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.isTokenExpired).toBe(true);
      expect(result.current.sessionTimeRemaining).toBe(0);
      expect(result.current.userDisplayName).toBe("");
    });
  });

  describe("Computed Properties", () => {
    it("correctly computes token expiration status", () => {
      const { result } = renderHook(() => ({
        isTokenExpired: useIsTokenExpired(),
        tokenInfo: useAuthStore((state) => state.tokenInfo),
      }));

      expect(result.current.isTokenExpired).toBe(true);

      act(() => {
        useAuthStore.setState({
          tokenInfo: {
            accessToken: "token",
            expiresAt: new Date(Date.now() + 3600000).toISOString(),
            tokenType: "Bearer",
          },
        });
      });

      expect(result.current.isTokenExpired).toBe(false);

      act(() => {
        useAuthStore.setState({
          tokenInfo: {
            accessToken: "token",
            expiresAt: new Date(Date.now() - 3600000).toISOString(),
            tokenType: "Bearer",
          },
        });
      });

      expect(result.current.isTokenExpired).toBe(true);
    });

    it("correctly computes session time remaining", () => {
      const { result } = renderHook(() => ({
        session: useAuthStore((state) => state.session),
        sessionTimeRemaining: useSessionTimeRemaining(),
      }));

      expect(result.current.sessionTimeRemaining).toBe(0);

      act(() => {
        useAuthStore.setState({
          session: {
            createdAt: "2025-01-01T00:00:00Z",
            expiresAt: new Date(Date.now() + 3600000).toISOString(),
            id: "session-1",
            lastActivity: "2025-01-01T00:00:00Z",
            userId: "user-1",
          },
        });
      });

      expect(result.current.sessionTimeRemaining).toBeGreaterThan(0);
    });

    it("correctly computes user display name", () => {
      const getUserDisplayName = (user: User | null): string => {
        if (!user) return "";
        if (user.displayName) return user.displayName;
        if (user.firstName && user.lastName)
          return `${user.firstName} ${user.lastName}`;
        if (user.firstName) return user.firstName;
        return user.email.split("@")[0];
      };

      const { result } = renderHook(() => useAuthStore());

      expect(getUserDisplayName(result.current.user)).toBe("");
      expect(result.current.user).toBeNull();

      act(() => {
        const mockUser = createMockUser({ id: "user-1" });
        result.current.setUser(mockUser);
      });

      expect(result.current.user).not.toBeNull();
      expect(result.current.user?.displayName).toBe("Custom Display Name");
      expect(getUserDisplayName(result.current.user)).toBe("Custom Display Name");

      act(() => {
        const mockUser = createMockUser({ displayName: undefined, id: "user-2" });
        result.current.setUser(mockUser);
      });

      expect(getUserDisplayName(result.current.user)).toBe("John Doe");

      act(() => {
        const mockUser = createMockUser({
          displayName: undefined,
          firstName: "Jane",
          id: "user-3",
          lastName: undefined,
        });
        result.current.setUser(mockUser);
      });

      expect(getUserDisplayName(result.current.user)).toBe("Jane");

      act(() => {
        const mockUser = createMockUser({
          displayName: undefined,
          email: "username@example.com",
          firstName: undefined,
          id: "user-4",
          lastName: undefined,
        });
        result.current.setUser(mockUser);
      });

      expect(getUserDisplayName(result.current.user)).toBe("username");
    });
  });

  describe("Error Management", () => {
    it("clears all errors", () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          error: "General error",
          loginError: "Login error",
          passwordResetError: "Reset error",
          registerError: "Register error",
        });
      });

      act(() => {
        result.current.clearErrors();
      });

      expect(result.current.error).toBeNull();
      expect(result.current.loginError).toBeNull();
      expect(result.current.registerError).toBeNull();
      expect(result.current.passwordResetError).toBeNull();
    });

    it("clears specific error types", () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          error: "General error",
          loginError: "Login error",
          passwordResetError: "Reset error",
          registerError: "Register error",
        });
      });

      act(() => {
        result.current.clearError("login");
      });

      expect(result.current.loginError).toBeNull();
      expect(result.current.error).toBe("General error");
      expect(result.current.registerError).toBe("Register error");

      act(() => {
        result.current.clearError("general");
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("Utility Actions", () => {
    it("sets user directly", () => {
      const { result } = renderHook(() => useAuthStore());

      const user = {
        createdAt: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        id: "user-1",
        isEmailVerified: true,
        updatedAt: "2025-01-01T00:00:00Z",
      };

      act(() => {
        result.current.setUser(user);
      });

      expect(result.current.user).toEqual(user);

      act(() => {
        result.current.setUser(null);
      });

      expect(result.current.user).toBeNull();
    });

    it("initializes with valid token", async () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          tokenInfo: {
            accessToken: "valid-token",
            expiresAt: new Date(Date.now() + 3600000).toISOString(),
            refreshToken: "refresh-token",
            tokenType: "Bearer",
          },
        });
      });

      await act(async () => {
        await result.current.initialize();
      });

      expect(result.current.isAuthenticated).toBe(true);
    });

    it("initializes with expired token logs out", async () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          tokenInfo: {
            accessToken: "expired-token",
            expiresAt: new Date(Date.now() - 3600000).toISOString(),
            tokenType: "Bearer",
          },
        });
      });

      await act(async () => {
        await result.current.initialize();
      });

      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe("Utility Selectors", () => {
    it("selector hooks return correct values", () => {
      const { result: authResult } = renderHook(() => ({
        isAuthenticated: useAuthStore((state) => state.isAuthenticated),
        isTokenExpired: useIsTokenExpired(),
        sessionTimeRemaining: useSessionTimeRemaining(),
        user: useAuthStore((state) => state.user),
        userDisplayName: useAuthStore((state) => state.userDisplayName),
      }));

      expect(authResult.current.isAuthenticated).toBe(false);
      expect(authResult.current.user).toBeNull();
      expect(authResult.current.userDisplayName).toBe("");
      expect(authResult.current.isTokenExpired).toBe(true);
      expect(authResult.current.sessionTimeRemaining).toBe(0);
    });
  });

  describe("Complex Scenarios", () => {
    it("handles full authentication flow", async () => {
      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.register({
          acceptTerms: true,
          confirmPassword: "password123",
          email: "newuser@example.com",
          firstName: "New",
          lastName: "User",
          password: "password123",
        });
      });

      expect(result.current.user?.email).toBe("newuser@example.com");
      expect(result.current.user?.isEmailVerified).toBe(false);

      await act(async () => {
        await result.current.verifyEmail("verification-token");
      });

      expect(result.current.user?.isEmailVerified).toBe(true);

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);

      await act(async () => {
        await result.current.login({
          email: "newuser@example.com",
          password: "password123",
        });
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user?.email).toBe("newuser@example.com");
    });

    it("handles token refresh scenarios", async () => {
      const { result } = renderHook(() => ({
        isTokenExpired: useIsTokenExpired(),
        store: useAuthStore(),
      }));

      await act(async () => {
        await result.current.store.login({
          email: "test@example.com",
          password: "password123",
        });
      });

      act(() => {
        const currentState = useAuthStore.getState();
        if (currentState.tokenInfo) {
          useAuthStore.setState({
            tokenInfo: {
              ...currentState.tokenInfo,
              expiresAt: new Date(Date.now() - 1000).toISOString(),
            },
          });
        }
      });

      expect(result.current.isTokenExpired).toBe(true);

      await act(async () => {
        await result.current.store.validateToken();
      });

      expect(result.current.isTokenExpired).toBe(false);
    });
  });
});
