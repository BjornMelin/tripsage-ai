import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthSession, AuthTokenInfo } from "@/lib/schemas/stores";
import {
  useAuthSession,
  useIsTokenExpired,
  useSessionTimeRemaining,
} from "@/stores/auth/auth-session";
import { resetAuthSlices, setupAuthSliceTests } from "./_shared";

// Mock fetch for API calls
global.fetch = vi.fn();

setupAuthSliceTests();

describe("AuthSession", () => {
  beforeEach(() => {
    resetAuthSlices();
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useAuthSession());

      expect(result.current.tokenInfo).toBeNull();
      expect(result.current.session).toBeNull();
      expect(result.current.isRefreshingToken).toBe(false);
    });

    it("computed properties work correctly with empty state", () => {
      const { result } = renderHook(() => ({
        isTokenExpired: useIsTokenExpired(),
        sessionTimeRemaining: useSessionTimeRemaining(),
      }));

      expect(result.current.isTokenExpired).toBe(true);
      expect(result.current.sessionTimeRemaining).toBe(0);
    });
  });

  describe("Token Management", () => {
    describe("Refresh Token", () => {
      it("successfully refreshes valid token", async () => {
        const mockTokenInfo: AuthTokenInfo = {
          accessToken: "new-access-token",
          expiresAt: new Date(Date.now() + 3600000).toISOString(),
          refreshToken: "refresh-token",
          tokenType: "Bearer",
        };
        const mockSession: AuthSession = {
          createdAt: "2025-01-01T00:00:00Z",
          expiresAt: new Date(Date.now() + 3600000).toISOString(),
          id: "session-1",
          lastActivity: "2025-01-01T00:00:00Z",
          userId: "user-1",
        };

        vi.mocked(fetch).mockResolvedValueOnce({
          json: async () => ({ session: mockSession, tokenInfo: mockTokenInfo }),
          ok: true,
        } as Response);

        const { result } = renderHook(() => useAuthSession());

        act(() => {
          useAuthSession.setState({
            tokenInfo: {
              accessToken: "old-token",
              expiresAt: new Date(Date.now() - 1000).toISOString(),
              refreshToken: "refresh-token",
              tokenType: "Bearer",
            },
          });
        });

        const originalToken = result.current.tokenInfo?.accessToken;

        let refreshResult: boolean | undefined;
        await act(async () => {
          refreshResult = await result.current.refreshToken();
        });

        expect(refreshResult).toBe(true);
        expect(result.current.tokenInfo?.accessToken).toBe("new-access-token");
        expect(result.current.tokenInfo?.accessToken).not.toBe(originalToken);
        expect(result.current.isRefreshingToken).toBe(false);
      });

      it("logs out when no refresh token available", async () => {
        const { result } = renderHook(() => useAuthSession());

        act(() => {
          useAuthSession.setState({
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
        expect(result.current.tokenInfo).toBeNull();
        expect(result.current.session).toBeNull();
      });

      it("handles refresh API error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: false,
        } as Response);

        const { result } = renderHook(() => useAuthSession());

        act(() => {
          useAuthSession.setState({
            tokenInfo: {
              accessToken: "old-token",
              expiresAt: new Date(Date.now() - 1000).toISOString(),
              refreshToken: "refresh-token",
              tokenType: "Bearer",
            },
          });
        });

        let refreshResult: boolean | undefined;
        await act(async () => {
          refreshResult = await result.current.refreshToken();
        });

        expect(refreshResult).toBe(false);
        expect(result.current.tokenInfo).toBeNull();
        expect(result.current.session).toBeNull();
      });
    });

    describe("Validate Token", () => {
      it("validates non-expired token", async () => {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: true,
        } as Response);

        const { result } = renderHook(() => useAuthSession());

        act(() => {
          useAuthSession.setState({
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
        const mockTokenInfo: AuthTokenInfo = {
          accessToken: "new-token",
          expiresAt: new Date(Date.now() + 3600000).toISOString(),
          refreshToken: "refresh-token",
          tokenType: "Bearer",
        };
        const mockSession: AuthSession = {
          createdAt: "2025-01-01T00:00:00Z",
          expiresAt: new Date(Date.now() + 3600000).toISOString(),
          id: "session-1",
          lastActivity: "2025-01-01T00:00:00Z",
          userId: "user-1",
        };

        vi.mocked(fetch)
          .mockResolvedValueOnce({
            json: async () => ({ session: mockSession, tokenInfo: mockTokenInfo }),
            ok: true,
          } as Response)
          .mockResolvedValueOnce({
            ok: true,
          } as Response);

        const { result } = renderHook(() => useAuthSession());

        act(() => {
          useAuthSession.setState({
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

  describe("Session Management", () => {
    beforeEach(() => {
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
    });

    it("extends session successfully", async () => {
      const newExpiresAt = new Date(Date.now() + 7200000).toISOString();
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({
          expiresAt: newExpiresAt,
          lastActivity: new Date().toISOString(),
        }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthSession());

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
      const mockSessions: AuthSession[] = [
        {
          createdAt: "2025-01-01T00:00:00Z",
          expiresAt: new Date(Date.now() + 3600000).toISOString(),
          id: "session-1",
          lastActivity: "2025-01-01T00:00:00Z",
          userId: "user-1",
        },
      ];

      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ sessions: mockSessions }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthSession());

      let sessions: AuthSession[] | undefined;
      await act(async () => {
        sessions = await result.current.getActiveSessions();
      });

      expect(sessions).toEqual(mockSessions);
    });

    it("revokes a session", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthSession());

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
        tokenInfo: useAuthSession((state) => state.tokenInfo),
      }));

      expect(result.current.isTokenExpired).toBe(true);

      act(() => {
        useAuthSession.setState({
          tokenInfo: {
            accessToken: "token",
            expiresAt: new Date(Date.now() + 3600000).toISOString(),
            tokenType: "Bearer",
          },
        });
      });

      expect(result.current.isTokenExpired).toBe(false);

      act(() => {
        useAuthSession.setState({
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
        session: useAuthSession((state) => state.session),
        sessionTimeRemaining: useSessionTimeRemaining(),
      }));

      expect(result.current.sessionTimeRemaining).toBe(0);

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

      expect(result.current.sessionTimeRemaining).toBeGreaterThan(0);
    });
  });

  describe("State Setters", () => {
    it("sets token info", () => {
      const { result } = renderHook(() => useAuthSession());

      const tokenInfo: AuthTokenInfo = {
        accessToken: "test-token",
        expiresAt: new Date(Date.now() + 3600000).toISOString(),
        tokenType: "Bearer",
      };

      act(() => {
        result.current.setTokenInfo(tokenInfo);
      });

      expect(result.current.tokenInfo).toEqual(tokenInfo);
    });

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
  });
});
