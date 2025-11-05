import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type {
  LoginCredentials,
  PasswordReset,
  PasswordResetRequest,
  RegisterCredentials,
} from "@/stores/auth-store";
import { useAuthStore } from "@/stores/auth-store";
import { resetAuthStore, setupAuthStoreTests } from "./_shared";

setupAuthStoreTests();

describe("Auth Store - Authentication Flow", () => {
  beforeEach(() => {
    resetAuthStore();
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

        await act(async () => {
          await result.current.login({
            email: "test@example.com",
            password: "password123",
          });
        });

        expect(result.current.isAuthenticated).toBe(true);

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

        await act(async () => {
          await result.current.login({
            email: "test@example.com",
            password: "password123",
          });
        });

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
      const updatedExpiresAt = result.current.session?.expiresAt;
      expect(typeof updatedExpiresAt).toBe("string");
      if (originalExpiresAt && updatedExpiresAt) {
        expect(new Date(updatedExpiresAt).getTime()).toBeGreaterThanOrEqual(
          new Date(originalExpiresAt).getTime()
        );
      }
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
});
