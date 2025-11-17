/**
 * @fileoverview Auth session slice - token management, refresh, session tracking.
 * Part of the composable auth store refactor (Phase 3).
 */

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import type { AuthSession, AuthTokenInfo } from "@/lib/schemas/stores";
import { isExpired, timeUntil } from "@/lib/stores/helpers";

/**
 * Auth session state interface.
 */
interface AuthSessionState {
  // State
  tokenInfo: AuthTokenInfo | null;
  session: AuthSession | null;
  isRefreshingToken: boolean;

  // Computed
  isTokenExpired: boolean;
  sessionTimeRemaining: number;

  // Actions
  refreshToken: () => Promise<boolean>;
  validateToken: () => Promise<boolean>;
  extendSession: () => Promise<boolean>;
  getActiveSessions: () => Promise<AuthSession[]>;
  revokeSession: (sessionId: string) => Promise<boolean>;
  setTokenInfo: (tokenInfo: AuthTokenInfo | null) => void;
  setSession: (session: AuthSession | null) => void;
}

/**
 * Auth session store hook.
 */
export const useAuthSession = create<AuthSessionState>()(
  devtools(
    persist(
      (set, get) => ({
        extendSession: async () => {
          const { session } = get();
          if (!session) return false;

          try {
            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/session/extend
            const response = await fetch("/api/auth/session/extend", {
              method: "POST",
            });

            if (!response.ok) {
              return false;
            }

            const data = await response.json();

            set({
              session: {
                ...session,
                expiresAt: data.expiresAt,
                lastActivity: data.lastActivity,
              },
            });

            return true;
          } catch (_error) {
            return false;
          }
        },

        getActiveSessions: async () => {
          try {
            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/sessions
            const response = await fetch("/api/auth/sessions", {
              method: "GET",
            });

            if (!response.ok) {
              return [];
            }

            const data = await response.json();
            return data.sessions || [];
          } catch (_error) {
            return [];
          }
        },
        isRefreshingToken: false,

        // Computed
        get isTokenExpired() {
          return isExpired(get().tokenInfo?.expiresAt ?? null);
        },

        // Actions
        refreshToken: async () => {
          const { tokenInfo } = get();

          if (!tokenInfo?.refreshToken) {
            return false;
          }

          set({ isRefreshingToken: true });

          try {
            // Call API route that uses createServerSupabase + withApiGuards
            // This endpoint handles cookie refresh via Supabase SSR
            // TODO: Replace with actual API call to /api/auth/refresh
            const response = await fetch("/api/auth/refresh", {
              body: JSON.stringify({
                refreshToken: tokenInfo.refreshToken,
              }),
              headers: { "Content-Type": "application/json" },
              method: "POST",
            });

            if (!response.ok) {
              throw new Error("Token refresh failed");
            }

            const data = await response.json();

            set({
              isRefreshingToken: false,
              session: data.session,
              tokenInfo: data.tokenInfo,
            });

            return true;
          } catch (_error) {
            set({ isRefreshingToken: false });
            // Clear tokens on refresh failure
            set({
              session: null,
              tokenInfo: null,
            });
            return false;
          }
        },

        revokeSession: async (sessionId) => {
          try {
            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/sessions/:id
            const response = await fetch(`/api/auth/sessions/${sessionId}`, {
              method: "DELETE",
            });

            return response.ok;
          } catch (_error) {
            return false;
          }
        },
        session: null,

        get sessionTimeRemaining() {
          return timeUntil(get().session?.expiresAt ?? null);
        },

        setSession: (session) => {
          set({ session });
        },

        setTokenInfo: (tokenInfo) => {
          set({ tokenInfo });
        },
        // Initial state
        tokenInfo: null,

        validateToken: async () => {
          const { tokenInfo, refreshToken } = get();

          if (!tokenInfo || isExpired(tokenInfo.expiresAt)) {
            return await refreshToken();
          }

          try {
            // Call API route that uses createServerSupabase to validate token
            // TODO: Replace with actual API call to /api/auth/validate
            const response = await fetch("/api/auth/validate", {
              body: JSON.stringify({
                accessToken: tokenInfo.accessToken,
              }),
              headers: { "Content-Type": "application/json" },
              method: "POST",
            });

            if (response.ok) {
              return true;
            }

            // If validation fails, try refresh
            return await refreshToken();
          } catch (_error) {
            // On error, try refresh
            return await refreshToken();
          }
        },
      }),
      {
        name: "auth-session-storage",
        partialize: (state) => ({
          session: state.session,
          tokenInfo: state.tokenInfo,
        }),
      }
    ),
    { name: "AuthSession" }
  )
);

// Selectors
export const useTokenInfo = () => useAuthSession((state) => state.tokenInfo);
export const useIsTokenExpired = () => useAuthSession((state) => state.isTokenExpired);
export const useSessionTimeRemaining = () =>
  useAuthSession((state) => state.sessionTimeRemaining);
