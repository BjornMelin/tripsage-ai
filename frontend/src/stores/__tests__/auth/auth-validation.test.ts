import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  PasswordReset,
  PasswordResetRequest,
} from "@/stores/auth/auth-validation";
import { useAuthValidation } from "@/stores/auth/auth-validation";
import { resetAuthSlices, setupAuthSliceTests } from "./_shared";

// Mock fetch for API calls
global.fetch = vi.fn();

setupAuthSliceTests();

describe("AuthValidation", () => {
  beforeEach(() => {
    resetAuthSlices();
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useAuthValidation());

      expect(result.current.isResettingPassword).toBe(false);
      expect(result.current.isVerifyingEmail).toBe(false);
      expect(result.current.passwordResetError).toBeNull();
      expect(result.current.registerError).toBeNull();
    });
  });

  describe("Password Reset Request", () => {
    it("successfully requests password reset", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

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
      const { result } = renderHook(() => useAuthValidation());

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

    it("handles password reset API error", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ message: "User not found" }),
        ok: false,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

      const request: PasswordResetRequest = {
        email: "test@example.com",
      };

      let resetResult: boolean | undefined;
      await act(async () => {
        resetResult = await result.current.requestPasswordReset(request);
      });

      expect(resetResult).toBe(false);
      expect(result.current.passwordResetError).toBe("User not found");
    });
  });

  describe("Password Reset", () => {
    it("successfully resets password with valid token", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

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
      const { result } = renderHook(() => useAuthValidation());

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
      const { result } = renderHook(() => useAuthValidation());

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
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

      let changeResult: boolean | undefined;
      await act(async () => {
        changeResult = await result.current.changePassword(
          "currentpassword",
          "newpassword123"
        );
      });

      expect(changeResult).toBe(true);
      expect(result.current.isResettingPassword).toBe(false);
    });

    it("handles change password with missing current password", async () => {
      const { result } = renderHook(() => useAuthValidation());

      let changeResult: boolean | undefined;
      await act(async () => {
        changeResult = await result.current.changePassword("", "newpassword123");
      });

      expect(changeResult).toBe(false);
      expect(result.current.passwordResetError).toBe(
        "Current and new passwords are required"
      );
    });

    it("handles change password API error", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ message: "Current password incorrect" }),
        ok: false,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

      let changeResult: boolean | undefined;
      await act(async () => {
        changeResult = await result.current.changePassword(
          "wrongpassword",
          "newpassword123"
        );
      });

      expect(changeResult).toBe(false);
      expect(result.current.passwordResetError).toBe("Current password incorrect");
    });
  });

  describe("Email Verification", () => {
    it("successfully verifies email", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

      let verifyResult: boolean | undefined;
      await act(async () => {
        verifyResult = await result.current.verifyEmail("valid-token");
      });

      expect(verifyResult).toBe(true);
      expect(result.current.isVerifyingEmail).toBe(false);
    });

    it("handles email verification API error", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ message: "Invalid token" }),
        ok: false,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

      let verifyResult: boolean | undefined;
      await act(async () => {
        verifyResult = await result.current.verifyEmail("invalid-token");
      });

      expect(verifyResult).toBe(false);
      expect(result.current.registerError).toBe("Invalid token");
    });

    it("successfully resends email verification", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

      let resendResult: boolean | undefined;
      await act(async () => {
        resendResult = await result.current.resendEmailVerification();
      });

      expect(resendResult).toBe(true);
      expect(result.current.isVerifyingEmail).toBe(false);
    });

    it("handles resend email verification API error", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ message: "Rate limit exceeded" }),
        ok: false,
      } as Response);

      const { result } = renderHook(() => useAuthValidation());

      let resendResult: boolean | undefined;
      await act(async () => {
        resendResult = await result.current.resendEmailVerification();
      });

      expect(resendResult).toBe(false);
      expect(result.current.registerError).toBe("Rate limit exceeded");
    });
  });

  describe("Error Management", () => {
    it("clears password reset error", () => {
      const { result } = renderHook(() => useAuthValidation());

      act(() => {
        useAuthValidation.setState({ passwordResetError: "Test error" });
      });

      expect(result.current.passwordResetError).toBe("Test error");

      act(() => {
        result.current.clearPasswordResetError();
      });

      expect(result.current.passwordResetError).toBeNull();
    });

    it("clears register error", () => {
      const { result } = renderHook(() => useAuthValidation());

      act(() => {
        useAuthValidation.setState({ registerError: "Test error" });
      });

      expect(result.current.registerError).toBe("Test error");

      act(() => {
        result.current.clearRegisterError();
      });

      expect(result.current.registerError).toBeNull();
    });
  });
});
