/**
 * @fileoverview Auth validation slice - password reset, email verification.
 * Part of the composable auth store refactor (Phase 3).
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";

/**
 * Interface for password reset request.
 */
export interface PasswordResetRequest {
  email: string;
}

/**
 * Interface for password reset.
 */
export interface PasswordReset {
  token: string;
  newPassword: string;
  confirmPassword: string;
}

/**
 * Auth validation state interface.
 */
interface AuthValidationState {
  // Loading states
  isResettingPassword: boolean;
  isVerifyingEmail: boolean;

  // Error states
  passwordResetError: string | null;
  registerError: string | null;

  // Actions
  requestPasswordReset: (request: PasswordResetRequest) => Promise<boolean>;
  resetPassword: (reset: PasswordReset) => Promise<boolean>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<boolean>;
  verifyEmail: (token: string) => Promise<boolean>;
  resendEmailVerification: () => Promise<boolean>;
  clearPasswordResetError: () => void;
  clearRegisterError: () => void;
}

/**
 * Auth validation store hook.
 */
export const useAuthValidation = create<AuthValidationState>()(
  devtools(
    (set) => ({
      changePassword: async (currentPassword, newPassword) => {
        set({ isResettingPassword: true, passwordResetError: null });

        try {
          if (!currentPassword || !newPassword) {
            throw new Error("Current and new passwords are required");
          }

          // Call API route that uses createServerSupabase + withApiGuards
          // TODO: Replace with actual API call to /api/auth/password/change
          const response = await fetch("/api/auth/password/change", {
            body: JSON.stringify({
              currentPassword,
              newPassword,
            }),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || "Password change failed");
          }

          set({ isResettingPassword: false });
          return true;
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Password change failed";
          set({
            isResettingPassword: false,
            passwordResetError: message,
          });
          return false;
        }
      },

      clearPasswordResetError: () => {
        set({ passwordResetError: null });
      },

      clearRegisterError: () => {
        set({ registerError: null });
      },
      // Initial state
      isResettingPassword: false,
      isVerifyingEmail: false,
      passwordResetError: null,
      registerError: null,

      // Actions
      requestPasswordReset: async (request) => {
        set({ isResettingPassword: true, passwordResetError: null });

        try {
          if (!request.email) {
            throw new Error("Email is required");
          }

          // Call API route that uses createServerSupabase + withApiGuards
          // Rate limiting is handled by withApiGuards + ROUTE_RATE_LIMITS
          // TODO: Replace with actual API call to /api/auth/password/reset-request
          const response = await fetch("/api/auth/password/reset-request", {
            body: JSON.stringify({ email: request.email }),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || "Password reset request failed");
          }

          set({ isResettingPassword: false });
          return true;
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Password reset request failed";
          set({
            isResettingPassword: false,
            passwordResetError: message,
          });
          return false;
        }
      },

      resendEmailVerification: async () => {
        set({ isVerifyingEmail: true });

        try {
          // Call API route that uses createServerSupabase + withApiGuards
          // Rate limiting is handled by withApiGuards + ROUTE_RATE_LIMITS
          // TODO: Replace with actual API call to /api/auth/email/resend
          const response = await fetch("/api/auth/email/resend", {
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || "Failed to resend verification email");
          }

          set({ isVerifyingEmail: false });
          return true;
        } catch (error) {
          const message =
            error instanceof Error
              ? error.message
              : "Failed to resend verification email";
          set({
            isVerifyingEmail: false,
            passwordResetError: message,
          });
          return false;
        }
      },

      resetPassword: async (reset) => {
        set({ isResettingPassword: true, passwordResetError: null });

        try {
          if (!reset.token || !reset.newPassword) {
            throw new Error("Token and new password are required");
          }

          if (reset.newPassword !== reset.confirmPassword) {
            throw new Error("Passwords do not match");
          }

          // Call API route that uses createServerSupabase + withApiGuards
          // TODO: Replace with actual API call to /api/auth/password/reset
          const response = await fetch("/api/auth/password/reset", {
            body: JSON.stringify({
              newPassword: reset.newPassword,
              token: reset.token,
            }),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || "Password reset failed");
          }

          set({ isResettingPassword: false });
          return true;
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Password reset failed";
          set({
            isResettingPassword: false,
            passwordResetError: message,
          });
          return false;
        }
      },

      verifyEmail: async (token) => {
        set({ isVerifyingEmail: true });

        try {
          // Call API route that uses createServerSupabase + withApiGuards
          // TODO: Replace with actual API call to /api/auth/email/verify
          const response = await fetch("/api/auth/email/verify", {
            body: JSON.stringify({ token }),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || "Email verification failed");
          }

          set({ isVerifyingEmail: false });
          return true;
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Email verification failed";
          set({
            isVerifyingEmail: false,
            passwordResetError: message,
          });
          return false;
        }
      },
    }),
    { name: "AuthValidation" }
  )
);

// Selectors
export const usePasswordResetError = () =>
  useAuthValidation((state) => state.passwordResetError);
export const useIsResettingPassword = () =>
  useAuthValidation((state) => state.isResettingPassword);
