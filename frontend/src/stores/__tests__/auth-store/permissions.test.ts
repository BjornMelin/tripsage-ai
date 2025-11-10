import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { UserPreferences, UserSecurity } from "@/stores/auth-store";
import { useAuthStore } from "@/stores/auth-store";
import { resetAuthStore, setupAuthStoreTests } from "./_shared";

setupAuthStoreTests();

describe("Auth Store - User Permissions", () => {
  beforeEach(async () => {
    resetAuthStore();
    const { result } = renderHook(() => useAuthStore());

    await act(async () => {
      await result.current.login({
        email: "test@example.com",
        password: "password123",
      });
    });
  });

  describe("User Management", () => {
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

        let resendResult: boolean | undefined;
        await act(async () => {
          resendResult = await result.current.resendEmailVerification();
        });

        expect(resendResult).toBe(false);
      });
    });
  });
});
