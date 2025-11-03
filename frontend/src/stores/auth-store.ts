import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Validation schemas
const USER_PREFERENCES_SCHEMA = z.object({
  analytics: z.boolean().optional(),
  autoSaveSearches: z.boolean().optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  language: z.string().optional(),
  locationServices: z.boolean().optional(),
  notifications: z
    .object({
      email: z.boolean().optional(),
      marketing: z.boolean().optional(),
      priceAlerts: z.boolean().optional(),
      tripReminders: z.boolean().optional(),
    })
    .optional(),
  smartSuggestions: z.boolean().optional(),
  theme: z.enum(["light", "dark", "system"]).optional(),
  timeFormat: z.enum(["12h", "24h"]).optional(),
  timezone: z.string().optional(),
  units: z.enum(["metric", "imperial"]).optional(),
});

const USER_SECURITY_SCHEMA = z.object({
  lastPasswordChange: z.string().optional(),
  securityQuestions: z
    .array(
      z.object({
        answer: z.string(), // This would be hashed in real implementation
        question: z.string(),
      })
    )
    .optional(),
  twoFactorEnabled: z.boolean().optional(),
});

const USER_SCHEMA = z.object({
  avatarUrl: z.string().url().optional(),
  bio: z.string().optional(),
  createdAt: z.string(),
  displayName: z.string().optional(),
  email: z.string().email(),
  firstName: z.string().optional(),
  id: z.string(),
  isEmailVerified: z.boolean(),
  lastName: z.string().optional(),
  location: z.string().optional(),
  preferences: USER_PREFERENCES_SCHEMA.optional(),
  security: USER_SECURITY_SCHEMA.optional(),
  updatedAt: z.string(),
  website: z.string().url().optional(),
});

const TOKEN_INFO_SCHEMA = z.object({
  accessToken: z.string(),
  expiresAt: z.string(),
  refreshToken: z.string().optional(),
  tokenType: z.string().default("Bearer"),
});

const SESSION_SCHEMA = z.object({
  createdAt: z.string(),
  deviceInfo: z
    .object({
      deviceId: z.string().optional(),
      ipAddress: z.string().optional(),
      userAgent: z.string().optional(),
    })
    .optional(),
  expiresAt: z.string(),
  id: z.string(),
  lastActivity: z.string(),
  userId: z.string(),
});

// Types derived from schemas
export type User = z.infer<typeof USER_SCHEMA>;
export type UserPreferences = z.infer<typeof USER_PREFERENCES_SCHEMA>;
export type UserSecurity = z.infer<typeof USER_SECURITY_SCHEMA>;
export type TokenInfo = z.infer<typeof TOKEN_INFO_SCHEMA>;
export type Session = z.infer<typeof SESSION_SCHEMA>;

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  confirmPassword: string;
  firstName?: string;
  lastName?: string;
  acceptTerms: boolean;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordReset {
  token: string;
  newPassword: string;
  confirmPassword: string;
}

// Authentication store interface
interface AuthState {
  // Authentication state
  isAuthenticated: boolean;
  user: User | null;
  tokenInfo: TokenInfo | null;
  session: Session | null;

  // Loading states
  isLoading: boolean;
  isLoggingIn: boolean;
  isRegistering: boolean;
  isResettingPassword: boolean;
  isRefreshingToken: boolean;

  // Error states
  error: string | null;
  loginError: string | null;
  registerError: string | null;
  passwordResetError: string | null;

  // Computed properties
  isTokenExpired: boolean;
  sessionTimeRemaining: number;
  userDisplayName: string;

  // Authentication actions
  login: (credentials: LoginCredentials) => Promise<boolean>;
  register: (credentials: RegisterCredentials) => Promise<boolean>;
  logout: () => Promise<void>;
  logoutAllDevices: () => Promise<void>;

  // Password management
  requestPasswordReset: (request: PasswordResetRequest) => Promise<boolean>;
  resetPassword: (reset: PasswordReset) => Promise<boolean>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<boolean>;

  // Token management
  refreshToken: () => Promise<boolean>;
  validateToken: () => Promise<boolean>;

  // User management
  updateUser: (updates: Partial<User>) => Promise<boolean>;
  updatePreferences: (preferences: Partial<UserPreferences>) => Promise<boolean>;
  updateSecurity: (security: Partial<UserSecurity>) => Promise<boolean>;
  verifyEmail: (token: string) => Promise<boolean>;
  resendEmailVerification: () => Promise<boolean>;

  // Session management
  extendSession: () => Promise<boolean>;
  getActiveSessions: () => Promise<Session[]>;
  revokeSession: (sessionId: string) => Promise<boolean>;

  // Utility actions
  clearErrors: () => void;
  clearError: (errorType: "login" | "register" | "passwordReset" | "general") => void;
  setUser: (user: User | null) => void;
  initialize: () => Promise<void>;
}

// Helper functions
const GENERATE_ID = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const GET_CURRENT_TIMESTAMP = () => new Date().toISOString();

// Token validation helper
const IS_TOKEN_EXPIRED = (tokenInfo: TokenInfo | null): boolean => {
  if (!tokenInfo) return true;
  return new Date() >= new Date(tokenInfo.expiresAt);
};

// Session time remaining helper
const GET_SESSION_TIME_REMAINING = (session: Session | null): number => {
  if (!session) return 0;
  const now = Date.now();
  const expiresAt = new Date(session.expiresAt).getTime();
  return Math.max(0, expiresAt - now);
};

// User display name helper
const GET_USER_DISPLAY_NAME = (user: User | null): string => {
  if (!user) return "";

  if (user.displayName) return user.displayName;
  if (user.firstName && user.lastName) return `${user.firstName} ${user.lastName}`;
  if (user.firstName) return user.firstName;
  return user.email.split("@")[0];
};

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set, get) => ({
        changePassword: async (currentPassword, newPassword) => {
          set({ isLoading: true });

          try {
            if (!currentPassword || !newPassword) {
              throw new Error("Current and new passwords are required");
            }

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({ isLoading: false });
            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Password change failed";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        clearError: (errorType) => {
          switch (errorType) {
            case "login":
              set({ loginError: null });
              break;
            case "register":
              set({ registerError: null });
              break;
            case "passwordReset":
              set({ passwordResetError: null });
              break;
            case "general":
              set({ error: null });
              break;
          }
        },

        // Utility actions
        clearErrors: () => {
          set({
            error: null,
            loginError: null,
            passwordResetError: null,
            registerError: null,
          });
        },

        // Error states
        error: null,

        // Session management
        extendSession: async () => {
          const { session } = get();
          if (!session) return false;

          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 200));

            const newExpiresAt = new Date(
              Date.now() + 24 * 60 * 60 * 1000
            ).toISOString();

            set({
              session: {
                ...session,
                expiresAt: newExpiresAt,
                lastActivity: GET_CURRENT_TIMESTAMP(),
              },
            });

            return true;
          } catch (_error) {
            return false;
          }
        },

        getActiveSessions: async () => {
          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            // Return mock sessions
            return [];
          } catch (_error) {
            return [];
          }
        },

        initialize: async () => {
          const { tokenInfo, validateToken } = get();

          if (tokenInfo && !IS_TOKEN_EXPIRED(tokenInfo)) {
            set({ isAuthenticated: true });
            await validateToken();
          } else {
            await get().logout();
          }
        },
        // Initial state
        isAuthenticated: false,

        // Loading states
        isLoading: false,
        isLoggingIn: false,
        isRefreshingToken: false,
        isRegistering: false,
        isResettingPassword: false,

        // Computed properties
        get isTokenExpired() {
          return IS_TOKEN_EXPIRED(get().tokenInfo);
        },

        // Authentication actions
        login: async (credentials) => {
          set({ isLoggingIn: true, loginError: null });

          try {
            // Validate credentials
            if (!credentials.email || !credentials.password) {
              throw new Error("Email and password are required");
            }

            // Mock API call - replace with actual implementation
            await new Promise((resolve) => setTimeout(resolve, 1000));

            // Mock successful login
            const now = GET_CURRENT_TIMESTAMP();
            const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(); // 24 hours

            const mockUser: User = {
              createdAt: now,
              displayName: credentials.email.split("@")[0],
              email: credentials.email,
              id: GENERATE_ID(),
              isEmailVerified: true,
              updatedAt: now,
            };

            const mockTokenInfo: TokenInfo = {
              accessToken: `mock_token_${GENERATE_ID()}`,
              expiresAt,
              refreshToken: `mock_refresh_${GENERATE_ID()}`,
              tokenType: "Bearer",
            };

            const mockSession: Session = {
              createdAt: now,
              expiresAt,
              id: GENERATE_ID(),
              lastActivity: now,
              userId: mockUser.id,
            };

            set({
              isAuthenticated: true,
              isLoggingIn: false,
              loginError: null,
              session: mockSession,
              tokenInfo: mockTokenInfo,
              user: mockUser,
            });

            return true;
          } catch (error) {
            const message = error instanceof Error ? error.message : "Login failed";
            set({
              isAuthenticated: false,
              isLoggingIn: false,
              loginError: message,
              session: null,
              tokenInfo: null,
              user: null,
            });
            return false;
          }
        },
        loginError: null,

        logout: async () => {
          set({ isLoading: true });

          try {
            // Mock API call to invalidate token
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              error: null,
              isAuthenticated: false,
              isLoading: false,
              loginError: null,
              passwordResetError: null,
              registerError: null,
              session: null,
              tokenInfo: null,
              user: null,
            });
          } catch (_error) {
            // Even if logout fails on server, clear local state
            set({
              isAuthenticated: false,
              isLoading: false,
              session: null,
              tokenInfo: null,
              user: null,
            });
          }
        },

        logoutAllDevices: async () => {
          set({ isLoading: true });

          try {
            // Mock API call to invalidate all sessions
            await new Promise((resolve) => setTimeout(resolve, 1000));

            await get().logout();
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to logout all devices";
            set({ error: message, isLoading: false });
          }
        },
        passwordResetError: null,

        // Token management
        refreshToken: async () => {
          const { tokenInfo } = get();

          if (!tokenInfo?.refreshToken) {
            await get().logout();
            return false;
          }

          set({ isRefreshingToken: true });

          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            const newExpiresAt = new Date(
              Date.now() + 24 * 60 * 60 * 1000
            ).toISOString();
            const newTokenInfo: TokenInfo = {
              ...tokenInfo,
              accessToken: `mock_token_${GENERATE_ID()}`,
              expiresAt: newExpiresAt,
            };

            set({
              isRefreshingToken: false,
              tokenInfo: newTokenInfo,
            });

            return true;
          } catch (_error) {
            set({ isRefreshingToken: false });
            await get().logout();
            return false;
          }
        },

        register: async (credentials) => {
          set({ isRegistering: true, registerError: null });

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

            // Mock API call - replace with actual implementation
            await new Promise((resolve) => setTimeout(resolve, 1000));

            // Mock successful registration
            const now = GET_CURRENT_TIMESTAMP();

            const mockUser: User = {
              createdAt: now,
              displayName: credentials.firstName
                ? `${credentials.firstName} ${credentials.lastName || ""}`.trim()
                : credentials.email.split("@")[0],
              email: credentials.email,
              firstName: credentials.firstName,
              id: GENERATE_ID(),
              isEmailVerified: false, // Requires email verification
              lastName: credentials.lastName,
              updatedAt: now,
            };

            set({
              isRegistering: false,
              registerError: null,
              user: mockUser,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Registration failed";
            set({
              isRegistering: false,
              registerError: message,
            });
            return false;
          }
        },
        registerError: null,

        // Password management
        requestPasswordReset: async (request) => {
          set({ isResettingPassword: true, passwordResetError: null });

          try {
            if (!request.email) {
              throw new Error("Email is required");
            }

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

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
          const { user } = get();
          if (!user || user.isEmailVerified) return false;

          set({ isLoading: true });

          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({ isLoading: false });
            return true;
          } catch (error) {
            const message =
              error instanceof Error
                ? error.message
                : "Failed to resend verification email";
            set({ error: message, isLoading: false });
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

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

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

        revokeSession: async (_sessionId) => {
          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            return true;
          } catch (_error) {
            return false;
          }
        },
        session: null,
        get sessionTimeRemaining() {
          return GET_SESSION_TIME_REMAINING(get().session);
        },

        setUser: (user) => {
          set({ user });
        },
        tokenInfo: null,

        updatePreferences: async (preferences) => {
          const { user } = get();
          if (!user) return false;

          set({ isLoading: true });

          try {
            const result = USER_PREFERENCES_SCHEMA.safeParse(preferences);
            if (!result.success) {
              throw new Error("Invalid preferences data");
            }

            const updatedUser = {
              ...user,
              preferences: {
                ...user.preferences,
                ...result.data,
              },
              updatedAt: GET_CURRENT_TIMESTAMP(),
            };

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              isLoading: false,
              user: updatedUser,
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
            const result = USER_SECURITY_SCHEMA.safeParse(security);
            if (!result.success) {
              throw new Error("Invalid security data");
            }

            const updatedUser = {
              ...user,
              security: {
                ...user.security,
                ...result.data,
              },
              updatedAt: GET_CURRENT_TIMESTAMP(),
            };

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({
              isLoading: false,
              user: updatedUser,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Security update failed";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        // User management
        updateUser: async (updates) => {
          const { user } = get();
          if (!user) return false;

          set({ isLoading: true });

          try {
            // Validate updates against schema
            const updatedUser = {
              ...user,
              ...updates,
              updatedAt: GET_CURRENT_TIMESTAMP(),
            };
            const result = USER_SCHEMA.safeParse(updatedUser);

            if (!result.success) {
              throw new Error("Invalid user data");
            }

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({
              isLoading: false,
              user: result.data,
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
        get userDisplayName() {
          return GET_USER_DISPLAY_NAME(get().user);
        },

        validateToken: async () => {
          const { tokenInfo } = get();

          if (!tokenInfo || IS_TOKEN_EXPIRED(tokenInfo)) {
            return await get().refreshToken();
          }

          try {
            // Mock API call to validate token
            await new Promise((resolve) => setTimeout(resolve, 200));
            return true;
          } catch (_error) {
            return await get().refreshToken();
          }
        },

        verifyEmail: async (_token) => {
          set({ isLoading: true });

          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            const { user } = get();
            if (user) {
              set({
                isLoading: false,
                user: {
                  ...user,
                  isEmailVerified: true,
                  updatedAt: GET_CURRENT_TIMESTAMP(),
                },
              });
            }

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Email verification failed";
            set({ error: message, isLoading: false });
            return false;
          }
        },
      }),
      {
        name: "auth-storage",
        partialize: (state) => ({
          isAuthenticated: state.isAuthenticated,
          tokenInfo: state.tokenInfo,
          // Persist user and token info, but not sensitive session data
          user: state.user,
        }),
      }
    ),
    { name: "AuthStore" }
  )
);

// Utility selectors for common use cases
export const useAuth = () =>
  useAuthStore((state) => ({
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    login: state.login,
    logout: state.logout,
    register: state.register,
    user: state.user,
  }));

export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
// Removed useUserDisplayName - now only exported from user-store.ts
export const useIsTokenExpired = () =>
  useAuthStore((state) => IS_TOKEN_EXPIRED(state.tokenInfo));
export const useSessionTimeRemaining = () =>
  useAuthStore((state) => GET_SESSION_TIME_REMAINING(state.session));
export const useAuthLoading = () =>
  useAuthStore((state) => ({
    isLoading: state.isLoading,
    isLoggingIn: state.isLoggingIn,
    isRegistering: state.isRegistering,
    isResettingPassword: state.isResettingPassword,
  }));
export const useAuthErrors = () =>
  useAuthStore((state) => ({
    error: state.error,
    loginError: state.loginError,
    passwordResetError: state.passwordResetError,
    registerError: state.registerError,
  }));
