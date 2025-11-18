/**
 * @fileoverview Auth core slice - login, register, user management.
 */

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import type { AuthUser } from "@/lib/schemas/stores";
import { getDisplayName } from "@/lib/stores/helpers";
import { useAuthSession } from "@/stores/auth/auth-session";

const computeUserDisplayName = (user: AuthUser | null): string => getDisplayName(user);

/**
 * Auth core state interface.
 */
interface AuthCoreState {
  // State
  isAuthenticated: boolean;
  user: AuthUser | null;
  error: string | null;
  isLoading: boolean;
  isLoggingIn: boolean;
  isRegistering: boolean;

  // Computed
  userDisplayName: string;

  // Actions
  logout: () => Promise<void>;
  setUser: (user: AuthUser | null) => void;
  clearError: () => void;
  initialize: () => Promise<void>;
}

/**
 * Initial auth core view-model state.
 * This state mirrors, but does not own, Supabase SSR session authority.
 */
export const authCoreInitialState: Pick<
  AuthCoreState,
  | "isAuthenticated"
  | "user"
  | "error"
  | "isLoading"
  | "isLoggingIn"
  | "isRegistering"
  | "userDisplayName"
> = {
  error: null,
  isAuthenticated: false,
  isLoading: false,
  isLoggingIn: false,
  isRegistering: false,
  user: null,
  userDisplayName: "",
};

/**
 * Auth core store hook.
 */
export const useAuthCore = create<AuthCoreState>()(
  devtools(
    persist(
      (set, _get) => ({
        // Initial state
        ...authCoreInitialState,

        clearError: () => {
          set({ error: null });
        },

        initialize: async () => {
          // Check if user is already authenticated via Supabase SSR session.
          try {
            const response = await fetch("/auth/me", {
              headers: { "Content-Type": "application/json" },
              method: "GET",
            });
            if (response.ok) {
              const data = (await response.json()) as { user: AuthUser | null };
              if (data.user) {
                set({
                  isAuthenticated: true,
                  user: data.user,
                  userDisplayName: computeUserDisplayName(data.user),
                });
                return;
              }
            }
          } catch (_error) {
            // Swallow errors and fall through to resetting state.
          }
          set({
            isAuthenticated: false,
            user: null,
            userDisplayName: "",
          });
        },

        logout: async () => {
          set({ isLoading: true });

          const clearSessionState = (): void => {
            const { resetSession } = useAuthSession.getState();
            resetSession();
          };

          try {
            // Call server route that uses createServerSupabase
            await fetch("/auth/logout", {
              method: "POST",
            });

            set({
              error: null,
              isAuthenticated: false,
              isLoading: false,
              user: null,
              userDisplayName: "",
            });
          } catch (_error) {
            // Even if logout fails on server, clear local state
            set({
              isAuthenticated: false,
              isLoading: false,
              user: null,
              userDisplayName: "",
            });
          } finally {
            clearSessionState();
          }
        },

        setUser: (user) => {
          set({
            user,
            userDisplayName: computeUserDisplayName(user),
          });
        },
        user: null,

        // Computed
        userDisplayName: "",
      }),
      {
        name: "auth-core-storage",
        partialize: (state) => ({
          isAuthenticated: state.isAuthenticated,
          user: state.user,
          userDisplayName: state.userDisplayName,
        }),
      }
    ),
    { name: "AuthCore" }
  )
);

// Selectors
export const useUser = () => useAuthCore((state) => state.user);
export const useIsAuthenticated = () => useAuthCore((state) => state.isAuthenticated);
export const useAuthLoading = () =>
  useAuthCore((state) => ({
    isLoading: state.isLoading,
    isLoggingIn: state.isLoggingIn,
    isRegistering: state.isRegistering,
  }));
export const useAuthError = () => useAuthCore((state) => state.error);
