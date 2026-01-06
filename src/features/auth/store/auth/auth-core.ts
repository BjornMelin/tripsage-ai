/**
 * @fileoverview Auth core slice - login, register, user management.
 */

import type { AuthUser } from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { useAuthSession } from "@/features/auth/store/auth/auth-session";
import { getDisplayName } from "@/features/shared/store/helpers";

const computeUserDisplayName = (user: AuthUser | null): string => getDisplayName(user);

/**
 * Auth core state interface.
 */
interface AuthCoreState {
  // State
  isAuthenticated: boolean;
  hasInitialized: boolean;
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
  | "hasInitialized"
  | "user"
  | "error"
  | "isLoading"
  | "isLoggingIn"
  | "isRegistering"
  | "userDisplayName"
> = {
  error: null,
  hasInitialized: false,
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
          if (_get().isLoading) return;
          set({ isLoading: true });

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
            set({
              isAuthenticated: false,
              user: null,
              userDisplayName: "",
            });
          } catch (_error) {
            // Swallow errors and fall through to resetting state.
            set({
              isAuthenticated: false,
              user: null,
              userDisplayName: "",
            });
          } finally {
            set({
              hasInitialized: true,
              isLoading: false,
            });
          }
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
