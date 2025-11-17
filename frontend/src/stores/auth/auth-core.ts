/**
 * @fileoverview Auth core slice - login, register, user management.
 */

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import type {
  AuthUser,
  AuthUserPreferences,
  AuthUserSecurity,
} from "@/lib/schemas/stores";
import { getCurrentTimestamp, getDisplayName } from "@/lib/stores/helpers";
import { useAuthSession } from "@/stores/auth/auth-session";

const computeUserDisplayName = (user: AuthUser | null): string => getDisplayName(user);

/**
 * Interface for login credentials.
 */
export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

/**
 * Interface for register credentials.
 */
export interface RegisterCredentials {
  email: string;
  password: string;
  confirmPassword: string;
  firstName?: string;
  lastName?: string;
  acceptTerms: boolean;
}

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
  login: (credentials: LoginCredentials) => Promise<boolean>;
  register: (credentials: RegisterCredentials) => Promise<boolean>;
  logout: () => Promise<void>;
  updateUser: (updates: Partial<AuthUser>) => Promise<boolean>;
  updatePreferences: (preferences: Partial<AuthUserPreferences>) => Promise<boolean>;
  updateSecurity: (security: Partial<AuthUserSecurity>) => Promise<boolean>;
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
      (set, get) => ({
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

        // Actions
        login: async (credentials) => {
          set({ error: null, isLoggingIn: true });

          try {
            // Validate credentials
            if (!credentials.email || !credentials.password) {
              throw new Error("Email and password are required");
            }

            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/login
            const response = await fetch("/api/auth/login", {
              body: JSON.stringify({
                email: credentials.email,
                password: credentials.password,
                rememberMe: credentials.rememberMe,
              }),
              headers: { "Content-Type": "application/json" },
              method: "POST",
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              throw new Error(errorData.message || "Login failed");
            }

            const data = await response.json();

            set({
              error: null,
              isAuthenticated: true,
              isLoggingIn: false,
              user: data.user,
              userDisplayName: computeUserDisplayName(data.user),
            });

            return true;
          } catch (error) {
            const message = error instanceof Error ? error.message : "Login failed";
            set({
              error: message,
              isAuthenticated: false,
              isLoggingIn: false,
              user: null,
              userDisplayName: "",
            });
            return false;
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

        register: async (credentials) => {
          set({ error: null, isRegistering: true });

          try {
            // Validate credentials
            if (!credentials.email || !credentials.password) {
              throw new Error("Email and password are required");
            }

            if (credentials.password !== credentials.confirmPassword) {
              throw new Error("Passwords do not match");
            }

            if (!credentials.acceptTerms) {
              throw new Error("You must accept the terms and conditions");
            }

            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/register
            const response = await fetch("/api/auth/register", {
              body: JSON.stringify({
                email: credentials.email,
                firstName: credentials.firstName,
                lastName: credentials.lastName,
                password: credentials.password,
              }),
              headers: { "Content-Type": "application/json" },
              method: "POST",
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              throw new Error(errorData.message || "Registration failed");
            }

            const data = await response.json();

            set({
              error: null,
              isRegistering: false,
              user: data.user,
              userDisplayName: computeUserDisplayName(data.user),
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Registration failed";
            set({
              error: message,
              isRegistering: false,
            });
            return false;
          }
        },

        setUser: (user) => {
          set({
            user,
            userDisplayName: computeUserDisplayName(user),
          });
        },

        updatePreferences: async (preferences) => {
          const { user } = get();
          if (!user) return false;

          set({ isLoading: true });

          try {
            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/preferences
            const response = await fetch("/api/auth/preferences", {
              body: JSON.stringify(preferences),
              headers: { "Content-Type": "application/json" },
              method: "PATCH",
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              throw new Error(errorData.message || "Preferences update failed");
            }

            const data = await response.json();

            const updatedUser = {
              ...user,
              preferences: {
                ...user.preferences,
                ...data.preferences,
              },
              updatedAt: data.user?.updatedAt || getCurrentTimestamp(),
            };

            set({
              error: null,
              isLoading: false,
              user: updatedUser,
              userDisplayName: computeUserDisplayName(updatedUser),
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Preferences update failed";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        updateSecurity: async (security) => {
          const { user } = get();
          if (!user) return false;

          set({ isLoading: true });

          try {
            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/security
            const response = await fetch("/api/auth/security", {
              body: JSON.stringify(security),
              headers: { "Content-Type": "application/json" },
              method: "PATCH",
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              throw new Error(errorData.message || "Security update failed");
            }

            const data = await response.json();

            const updatedUser = {
              ...user,
              security: {
                ...user.security,
                ...data.security,
              },
              updatedAt: data.user?.updatedAt || getCurrentTimestamp(),
            };

            set({
              error: null,
              isLoading: false,
              user: updatedUser,
              userDisplayName: computeUserDisplayName(updatedUser),
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Security update failed";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        updateUser: async (updates) => {
          const { user } = get();
          if (!user) return false;

          set({ isLoading: true });

          try {
            // Call API route that uses createServerSupabase + withApiGuards
            // TODO: Replace with actual API call to /api/auth/user
            const response = await fetch("/api/auth/user", {
              body: JSON.stringify(updates),
              headers: { "Content-Type": "application/json" },
              method: "PATCH",
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              throw new Error(errorData.message || "User update failed");
            }

            const data = await response.json();

            const updatedUser = {
              ...user,
              ...data.user,
              updatedAt: data.user?.updatedAt || getCurrentTimestamp(),
            };

            set({
              error: null,
              isLoading: false,
              user: updatedUser,
              userDisplayName: computeUserDisplayName(updatedUser),
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "User update failed";
            set({ error: message, isLoading: false });
            return false;
          }
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
