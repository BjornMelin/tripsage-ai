import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/stores/auth-store";
import { resetAuthStore, setupAuthStoreTests } from "./_shared";

setupAuthStoreTests();

describe("Auth Store - Token Management", () => {
  beforeEach(() => {
    resetAuthStore();
  });

  describe("Token Management", () => {
    describe("Refresh Token", () => {
      it("successfully refreshes valid token", async () => {
        const { result } = renderHook(() => useAuthStore());

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
});
