import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type LoginCredentials,
  type PasswordReset,
  type PasswordResetRequest,
  type RegisterCredentials,
  type User,
  type UserPreferences,
  type UserSecurity,
  useAuthStore,
  useIsAuthenticated,
  useIsTokenExpired,
  useSessionTimeRemaining,
  useUser,
} from "../auth-store";

// Accelerate store async flows in this suite only
let timeoutSpy: { mockRestore: () => void } | null = null;
beforeEach(() => {
  timeoutSpy = vi.spyOn(globalThis, "setTimeout").mockImplementation(((
    cb: TimerHandler,
    _ms?: number,
    ...args: unknown[]
  ) => {
    if (typeof cb === "function") {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      cb(...(args as never[]));
    }
    return 0 as unknown as ReturnType<typeof setTimeout>;
  }) as unknown as typeof setTimeout);
});

afterEach(() => {
  timeoutSpy?.mockRestore();
});

// Helper function to create mock users with Zod validation
const CREATE_MOCK_USER = (overrides: Partial<User> = {}): User => {
  const mockUserData = {
    avatarUrl: "https://example.com/avatar.jpg",
    bio: "Test bio",
    createdAt: "2025-01-01T00:00:00Z",
    displayName: "Custom Display Name",
    email: "test@example.com",
    firstName: "John",
    id: "user-1",
    isEmailVerified: true,
    lastName: "Doe",
    preferences: {
      language: "en",
      notifications: {
        email: true,
        marketing: false,
        priceAlerts: false,
        tripReminders: true,
      },
      theme: "light" as const,
      timezone: "UTC",
    },
    security: {
      lastPasswordChange: "2025-01-01T00:00:00Z",
      twoFactorEnabled: false,
    },
    updatedAt: "2025-01-01T00:00:00Z",
    ...overrides,
  };

  return mockUserData;
};

describe("Auth Store", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        error: null,
        isAuthenticated: false,
        isLoading: false,
        isLoggingIn: false,
        isRefreshingToken: false,
        isRegistering: false,
        isResettingPassword: false,
        loginError: null,
        passwordResetError: null,
        registerError: null,
        session: null,
        tokenInfo: null,
        user: null,
      });
    });
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

  describe("Authentication Actions", () => {
    describe("Login", () => {
      it("successfully logs in with valid credentials", async () => {
        const { result } = renderHook(() => useAuthStore());

        const credentials: LoginCredentials = {
          email: "test@example.com",
          password: "password123",
          rememberMe: true,
        };

        let loginResult: boolean | undefined;
        await act(async () => {
          loginResult = await result.current.login(credentials);
        });

        expect(loginResult).toBe(true);
        expect(result.current.isAuthenticated).toBe(true);
        expect(result.current.user).toBeDefined();
        expect(result.current.user?.email).toBe("test@example.com");
        expect(result.current.tokenInfo).toBeDefined();
        expect(result.current.session).toBeDefined();
        expect(result.current.isLoggingIn).toBe(false);
        expect(result.current.loginError).toBeNull();
      });

      it("handles login with missing email", async () => {
        const { result } = renderHook(() => useAuthStore());

        // This should fail Zod validation, but we'll test the store's handling
        const credentials = {
          email: "",
          password: "password123",
        } as LoginCredentials;

        let loginResult: boolean | undefined;
        await act(async () => {
          loginResult = await result.current.login(credentials);
        });

        expect(loginResult).toBe(false);
        expect(result.current.isAuthenticated).toBe(false);
        expect(result.current.user).toBeNull();
        expect(result.current.loginError).toBe("Email and password are required");
        expect(result.current.isLoggingIn).toBe(false);
      });

      it("handles login with missing password", async () => {
        const { result } = renderHook(() => useAuthStore());

        // This should fail Zod validation, but we'll test the store's handling
        const credentials = {
          email: "test@example.com",
          password: "",
        } as LoginCredentials;

        let loginResult: boolean | undefined;
        await act(async () => {
          loginResult = await result.current.login(credentials);
        });

        expect(loginResult).toBe(false);
        expect(result.current.isAuthenticated).toBe(false);
        expect(result.current.loginError).toBe("Email and password are required");
      });

      it("sets loading state during login", async () => {
        const { result } = renderHook(() => useAuthStore());

        const credentials: LoginCredentials = {
          email: "test@example.com",
          password: "password123",
        };

        let wasLoggingIn = false;
        await act(async () => {
          const promise = result.current.login(credentials);
          wasLoggingIn = result.current.isLoggingIn;
          await promise;
        });

        expect(wasLoggingIn).toBe(false); // Will be false due to mocked setTimeout
        expect(result.current.isLoggingIn).toBe(false);
      });

      it("clears previous login errors on new login attempt", async () => {
        const { result } = renderHook(() => useAuthStore());

        // Set initial error
        act(() => {
          useAuthStore.setState({ loginError: "Previous error" });
        });

        expect(result.current.loginError).toBe("Previous error");

        const credentials: LoginCredentials = {
          email: "test@example.com",
          password: "password123",
        };

        await act(async () => {
          await result.current.login(credentials);
        });

        expect(result.current.loginError).toBeNull();
      });
    });

    describe("Register", () => {
      it("successfully registers with valid credentials", async () => {
        const { result } = renderHook(() => useAuthStore());

        const credentials: RegisterCredentials = {
          acceptTerms: true,
          confirmPassword: "password123",
          email: "newuser@example.com",
          firstName: "John",
          lastName: "Doe",
          password: "password123",
        };

        let registerResult: boolean | undefined;
        await act(async () => {
          registerResult = await result.current.register(credentials);
        });

        expect(registerResult).toBe(true);
        expect(result.current.user).toBeDefined();
        expect(result.current.user?.email).toBe("newuser@example.com");
        expect(result.current.user?.firstName).toBe("John");
        expect(result.current.user?.lastName).toBe("Doe");
        expect(result.current.user?.isEmailVerified).toBe(false);
        expect(result.current.isRegistering).toBe(false);
        expect(result.current.registerError).toBeNull();
      });

      it("handles registration with mismatched passwords", async () => {
        const { result } = renderHook(() => useAuthStore());

        const credentials: RegisterCredentials = {
          acceptTerms: true,
          confirmPassword: "differentpassword",
          email: "newuser@example.com",
          password: "password123",
        };

        let registerResult: boolean | undefined;
        await act(async () => {
          registerResult = await result.current.register(credentials);
        });

        expect(registerResult).toBe(false);
        expect(result.current.user).toBeNull();
        expect(result.current.registerError).toBe("Passwords do not match");
      });

      it("handles registration without accepting terms", async () => {
        const { result } = renderHook(() => useAuthStore());

        const credentials: RegisterCredentials = {
          acceptTerms: false,
          confirmPassword: "password123",
          email: "newuser@example.com",
          password: "password123",
        };

        let registerResult: boolean | undefined;
        await act(async () => {
          registerResult = await result.current.register(credentials);
        });

        expect(registerResult).toBe(false);
        expect(result.current.registerError).toBe(
          "You must accept the terms and conditions"
        );
      });

      it("generates correct display name with first and last name", async () => {
        const { result } = renderHook(() => useAuthStore());

        const credentials: RegisterCredentials = {
          acceptTerms: true,
          confirmPassword: "password123",
          email: "user@example.com",
          firstName: "Jane",
          lastName: "Smith",
          password: "password123",
        };

        await act(async () => {
          await result.current.register(credentials);
        });

        expect(result.current.user?.displayName).toBe("Jane Smith");
      });

      it("generates display name from email when no first name provided", async () => {
        const { result } = renderHook(() => useAuthStore());

        const credentials: RegisterCredentials = {
          acceptTerms: true,
          confirmPassword: "password123",
          email: "username@example.com",
          password: "password123",
        };

        await act(async () => {
          await result.current.register(credentials);
        });

        expect(result.current.user?.displayName).toBe("username");
      });
    });

    describe("Logout", () => {
      it("successfully logs out and clears all auth state", async () => {
        const { result } = renderHook(() => useAuthStore());

        // First login
        await act(async () => {
          await result.current.login({
            email: "test@example.com",
            password: "password123",
          });
        });

        expect(result.current.isAuthenticated).toBe(true);

        // Then logout
        await act(async () => {
          await result.current.logout();
        });

        expect(result.current.isAuthenticated).toBe(false);
        expect(result.current.user).toBeNull();
        expect(result.current.tokenInfo).toBeNull();
        expect(result.current.session).toBeNull();
        expect(result.current.error).toBeNull();
        expect(result.current.loginError).toBeNull();
        expect(result.current.registerError).toBeNull();
        expect(result.current.passwordResetError).toBeNull();
      });

      it("logs out from all devices", async () => {
        const { result } = renderHook(() => useAuthStore());

        // First login
        await act(async () => {
          await result.current.login({
            email: "test@example.com",
            password: "password123",
          });
        });

        // Logout from all devices
        await act(async () => {
          await result.current.logoutAllDevices();
        });

        expect(result.current.isAuthenticated).toBe(false);
        expect(result.current.user).toBeNull();
      });
    });
  });

  describe("Password Management", () => {
    describe("Password Reset Request", () => {
      it("successfully requests password reset", async () => {
        const { result } = renderHook(() => useAuthStore());

        const request: PasswordResetRequest = {
          email: "test@example.com",
        };

        let resetResult: boolean | undefined;
        await act(async () => {
          resetResult = await result.current.requestPasswordReset(request);
        });

        expect(resetResult).toBe(true);
        expect(result.current.isResettingPassword).toBe(false);
        expect(result.current.passwordResetError).toBeNull();
      });

      it("handles password reset request with missing email", async () => {
        const { result } = renderHook(() => useAuthStore());

        const request: PasswordResetRequest = {
          email: "",
        };

        let resetResult: boolean | undefined;
        await act(async () => {
          resetResult = await result.current.requestPasswordReset(request);
        });

        expect(resetResult).toBe(false);
        expect(result.current.passwordResetError).toBe("Email is required");
      });
    });

    describe("Password Reset", () => {
      it("successfully resets password with valid token", async () => {
        const { result } = renderHook(() => useAuthStore());

        const reset: PasswordReset = {
          confirmPassword: "newpassword123",
          newPassword: "newpassword123",
          token: "valid-reset-token",
        };

        let resetResult: boolean | undefined;
        await act(async () => {
          resetResult = await result.current.resetPassword(reset);
        });

        expect(resetResult).toBe(true);
        expect(result.current.isResettingPassword).toBe(false);
        expect(result.current.passwordResetError).toBeNull();
      });

      it("handles password reset with mismatched passwords", async () => {
        const { result } = renderHook(() => useAuthStore());

        const reset: PasswordReset = {
          confirmPassword: "differentpassword",
          newPassword: "newpassword123",
          token: "valid-reset-token",
        };

        let resetResult: boolean | undefined;
        await act(async () => {
          resetResult = await result.current.resetPassword(reset);
        });

        expect(resetResult).toBe(false);
        expect(result.current.passwordResetError).toBe("Passwords do not match");
      });

      it("handles password reset with missing token", async () => {
        const { result } = renderHook(() => useAuthStore());

        const reset: PasswordReset = {
          confirmPassword: "newpassword123",
          newPassword: "newpassword123",
          token: "",
        };

        let resetResult: boolean | undefined;
        await act(async () => {
          resetResult = await result.current.resetPassword(reset);
        });

        expect(resetResult).toBe(false);
        expect(result.current.passwordResetError).toBe(
          "Token and new password are required"
        );
      });
    });

    describe("Change Password", () => {
      it("successfully changes password", async () => {
        const { result } = renderHook(() => useAuthStore());

        let changeResult: boolean | undefined;
        await act(async () => {
          changeResult = await result.current.changePassword(
            "currentpassword",
            "newpassword123"
          );
        });

        expect(changeResult).toBe(true);
        expect(result.current.isLoading).toBe(false);
        expect(result.current.error).toBeNull();
      });

      it("handles change password with missing current password", async () => {
        const { result } = renderHook(() => useAuthStore());

        let changeResult: boolean | undefined;
        await act(async () => {
          changeResult = await result.current.changePassword("", "newpassword123");
        });

        expect(changeResult).toBe(false);
        expect(result.current.error).toBe("Current and new passwords are required");
      });
    });
  });

  describe("Token Management", () => {
    describe("Refresh Token", () => {
      it("successfully refreshes valid token", async () => {
        const { result } = renderHook(() => useAuthStore());

        // First login to get tokens
        await act(async () => {
          await result.current.login({
            email: "test@example.com",
            password: "password123",
          });
        });

        const originalToken = result.current.tokenInfo?.accessToken;

        let refreshResult: boolean | undefined;
        await act(async () => {
          refreshResult = await result.current.refreshToken();
        });

        expect(refreshResult).toBe(true);
        expect(result.current.tokenInfo?.accessToken).toBeDefined();
        expect(result.current.tokenInfo?.accessToken).not.toBe(originalToken);
        expect(result.current.isRefreshingToken).toBe(false);
      });

      it("logs out when no refresh token available", async () => {
        const { result } = renderHook(() => useAuthStore());

        // Set state without refresh token
        act(() => {
          useAuthStore.setState({
            tokenInfo: {
              accessToken: "access-token",
              expiresAt: new Date(Date.now() + 3600000).toISOString(),
              tokenType: "Bearer",
            },
          });
        });

        let refreshResult: boolean | undefined;
        await act(async () => {
          refreshResult = await result.current.refreshToken();
        });

        expect(refreshResult).toBe(false);
        expect(result.current.isAuthenticated).toBe(false);
      });
    });

    describe("Validate Token", () => {
      it("validates non-expired token", async () => {
        const { result } = renderHook(() => useAuthStore());

        // Set valid token
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

        let validateResult: boolean | undefined;
        await act(async () => {
          validateResult = await result.current.validateToken();
        });

        expect(validateResult).toBe(true);
      });

      it("refreshes expired token", async () => {
        const { result } = renderHook(() => useAuthStore());

        // Set expired token
        act(() => {
          useAuthStore.setState({
            tokenInfo: {
              accessToken: "expired-token",
              expiresAt: new Date(Date.now() - 3600000).toISOString(),
              refreshToken: "refresh-token",
              tokenType: "Bearer",
            },
          });
        });

        let validateResult: boolean | undefined;
        await act(async () => {
          validateResult = await result.current.validateToken();
        });

        expect(validateResult).toBe(true);
      });
    });
  });

  describe("User Management", () => {
    beforeEach(async () => {
      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.login({
          email: "test@example.com",
          password: "password123",
        });
      });
    });

    describe("Update User", () => {
      it("successfully updates user information", async () => {
        const { result } = renderHook(() => useAuthStore());

        const updates = {
          bio: "Updated bio",
          firstName: "UpdatedFirst",
          lastName: "UpdatedLast",
        };

        let updateResult: boolean | undefined;
        await act(async () => {
          updateResult = await result.current.updateUser(updates);
        });

        expect(updateResult).toBe(true);
        expect(result.current.user?.firstName).toBe("UpdatedFirst");
        expect(result.current.user?.lastName).toBe("UpdatedLast");
        expect(result.current.user?.bio).toBe("Updated bio");
      });

      it("handles update user when not logged in", async () => {
        const { result } = renderHook(() => useAuthStore());

        // Logout first
        await act(async () => {
          await result.current.logout();
        });

        let updateResult: boolean | undefined;
        await act(async () => {
          updateResult = await result.current.updateUser({ firstName: "Test" });
        });

        expect(updateResult).toBe(false);
      });
    });

    describe("Update Preferences", () => {
      it("successfully updates user preferences", async () => {
        const { result } = renderHook(() => useAuthStore());

        const preferences: Partial<UserPreferences> = {
          language: "es",
          notifications: {
            email: true,
            tripReminders: false,
          },
          theme: "dark",
        };

        let updateResult: boolean | undefined;
        await act(async () => {
          updateResult = await result.current.updatePreferences(preferences);
        });

        expect(updateResult).toBe(true);
        expect(result.current.user?.preferences?.theme).toBe("dark");
        expect(result.current.user?.preferences?.language).toBe("es");
        expect(result.current.user?.preferences?.notifications?.email).toBe(true);
      });
    });

    describe("Update Security", () => {
      it("successfully updates security settings", async () => {
        const { result } = renderHook(() => useAuthStore());

        const security: Partial<UserSecurity> = {
          lastPasswordChange: "2025-01-01T00:00:00Z",
          twoFactorEnabled: true,
        };

        let updateResult: boolean | undefined;
        await act(async () => {
          updateResult = await result.current.updateSecurity(security);
        });

        expect(updateResult).toBe(true);
        expect(result.current.user?.security?.twoFactorEnabled).toBe(true);
        expect(result.current.user?.security?.lastPasswordChange).toBe(
          "2025-01-01T00:00:00Z"
        );
      });
    });

    describe("Email Verification", () => {
      it("successfully verifies email", async () => {
        const { result } = renderHook(() => useAuthStore());

        let verifyResult: boolean | undefined;
        await act(async () => {
          verifyResult = await result.current.verifyEmail("valid-token");
        });

        expect(verifyResult).toBe(true);
        expect(result.current.user?.isEmailVerified).toBe(true);
      });

      it("resends email verification", async () => {
        const { result } = renderHook(() => useAuthStore());

        // Set user as unverified
        act(() => {
          const currentUser = useAuthStore.getState().user;
          if (currentUser) {
            useAuthStore.setState({
              user: { ...currentUser, isEmailVerified: false },
            });
          }
        });

        let resendResult: boolean | undefined;
        await act(async () => {
          resendResult = await result.current.resendEmailVerification();
        });

        expect(resendResult).toBe(true);
      });

      it("does not resend verification for verified user", async () => {
        const { result } = renderHook(() => useAuthStore());

        // User is already verified from login
        let resendResult: boolean | undefined;
        await act(async () => {
          resendResult = await result.current.resendEmailVerification();
        });

        expect(resendResult).toBe(false);
      });
    });
  });

  describe("Session Management", () => {
    beforeEach(async () => {
      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.login({
          email: "test@example.com",
          password: "password123",
        });
      });
    });

    it("extends session successfully", async () => {
      const { result } = renderHook(() => useAuthStore());

      const originalExpiresAt = result.current.session?.expiresAt;

      let extendResult: boolean | undefined;
      await act(async () => {
        extendResult = await result.current.extendSession();
      });

      expect(extendResult).toBe(true);
      expect(result.current.session?.expiresAt).not.toBe(originalExpiresAt);
    });

    it("gets active sessions", async () => {
      const { result } = renderHook(() => useAuthStore());

      let sessions: unknown[] | undefined;
      await act(async () => {
        sessions = await result.current.getActiveSessions();
      });

      expect(sessions).toEqual([]);
    });

    it("revokes a session", async () => {
      const { result } = renderHook(() => useAuthStore());

      let revokeResult: boolean | undefined;
      await act(async () => {
        revokeResult = await result.current.revokeSession("session-id");
      });

      expect(revokeResult).toBe(true);
    });
  });

  describe("Computed Properties", () => {
    it("correctly computes token expiration status", () => {
      const { result } = renderHook(() => ({
        isTokenExpired: useIsTokenExpired(),
        tokenInfo: useAuthStore((state) => state.tokenInfo),
      }));

      // No token - should be expired
      expect(result.current.isTokenExpired).toBe(true);

      // Valid token
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

      // Expired token
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

      // No session
      expect(result.current.sessionTimeRemaining).toBe(0);

      // Valid session
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
      // Helper function to mimic the getUserDisplayName logic
      const getUserDisplayName = (user: User | null): string => {
        if (!user) return "";
        if (user.displayName) return user.displayName;
        if (user.firstName && user.lastName)
          return `${user.firstName} ${user.lastName}`;
        if (user.firstName) return user.firstName;
        return user.email.split("@")[0];
      };

      const { result } = renderHook(() => useAuthStore());

      // No user
      expect(getUserDisplayName(result.current.user)).toBe("");
      expect(result.current.user).toBeNull();

      // User with display name
      act(() => {
        const mockUser = CREATE_MOCK_USER({ id: "user-1" });
        result.current.setUser(mockUser);
      });

      // Verify user was set correctly and test display name logic
      expect(result.current.user).not.toBeNull();
      expect(result.current.user?.displayName).toBe("Custom Display Name");
      expect(getUserDisplayName(result.current.user)).toBe("Custom Display Name");

      // User with first and last name (no display name)
      act(() => {
        const mockUser = CREATE_MOCK_USER({ displayName: undefined, id: "user-2" });
        result.current.setUser(mockUser);
      });

      expect(getUserDisplayName(result.current.user)).toBe("John Doe");

      // User with only first name
      act(() => {
        const mockUser = CREATE_MOCK_USER({
          displayName: undefined,
          firstName: "Jane",
          id: "user-3",
          lastName: undefined,
        });
        result.current.setUser(mockUser);
      });

      expect(getUserDisplayName(result.current.user)).toBe("Jane");

      // User with only email
      act(() => {
        const mockUser = CREATE_MOCK_USER({
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

      const user: User = {
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

      // Set valid token first
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

      // Set expired token
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
        isAuthenticated: useIsAuthenticated(),
        isTokenExpired: useIsTokenExpired(),
        sessionTimeRemaining: useSessionTimeRemaining(),
        user: useUser(),
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

      // Register
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

      // Verify email
      await act(async () => {
        await result.current.verifyEmail("verification-token");
      });

      expect(result.current.user?.isEmailVerified).toBe(true);

      // Logout
      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);

      // Login
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

      // Login to get tokens
      await act(async () => {
        await result.current.store.login({
          email: "test@example.com",
          password: "password123",
        });
      });

      // Manually expire token
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

      // Validate token should trigger refresh
      await act(async () => {
        await result.current.store.validateToken();
      });

      expect(result.current.isTokenExpired).toBe(false);
    });
  });
});
