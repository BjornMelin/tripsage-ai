import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Validation schemas
const UserPreferencesSchema = z.object({
  language: z.string().optional(),
  timezone: z.string().optional(),
  theme: z.enum(["light", "dark", "system"]).optional(),
  units: z.enum(["metric", "imperial"]).optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  timeFormat: z.enum(["12h", "24h"]).optional(),
  notifications: z
    .object({
      email: z.boolean().optional(),
      tripReminders: z.boolean().optional(),
      priceAlerts: z.boolean().optional(),
      marketing: z.boolean().optional(),
    })
    .optional(),
  autoSaveSearches: z.boolean().optional(),
  smartSuggestions: z.boolean().optional(),
  locationServices: z.boolean().optional(),
  analytics: z.boolean().optional(),
});

const UserSecuritySchema = z.object({
  twoFactorEnabled: z.boolean().optional(),
  lastPasswordChange: z.string().optional(),
  securityQuestions: z
    .array(
      z.object({
        question: z.string(),
        answer: z.string(), // This would be hashed in real implementation
      })
    )
    .optional(),
});

const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  displayName: z.string().optional(),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  avatarUrl: z.string().url().optional(),
  isEmailVerified: z.boolean(),
  bio: z.string().optional(),
  location: z.string().optional(),
  website: z.string().url().optional(),
  preferences: UserPreferencesSchema.optional(),
  security: UserSecuritySchema.optional(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

const TokenInfoSchema = z.object({
  accessToken: z.string(),
  refreshToken: z.string().optional(),
  expiresAt: z.string(),
  tokenType: z.string().default("Bearer"),
});

const SessionSchema = z.object({
  id: z.string(),
  userId: z.string(),
  deviceInfo: z
    .object({
      userAgent: z.string().optional(),
      ipAddress: z.string().optional(),
      deviceId: z.string().optional(),
    })
    .optional(),
  createdAt: z.string(),
  lastActivity: z.string(),
  expiresAt: z.string(),
});

// Types derived from schemas
export type User = z.infer<typeof UserSchema>;
export type UserPreferences = z.infer<typeof UserPreferencesSchema>;
export type UserSecurity = z.infer<typeof UserSecuritySchema>;
export type TokenInfo = z.infer<typeof TokenInfoSchema>;
export type Session = z.infer<typeof SessionSchema>;

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
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

// Token validation helper
const isTokenExpired = (tokenInfo: TokenInfo | null): boolean => {
  if (!tokenInfo) return true;
  return new Date() >= new Date(tokenInfo.expiresAt);
};

// Session time remaining helper
const getSessionTimeRemaining = (session: Session | null): number => {
  if (!session) return 0;
  const now = new Date().getTime();
  const expiresAt = new Date(session.expiresAt).getTime();
  return Math.max(0, expiresAt - now);
};

// User display name helper
const getUserDisplayName = (user: User | null): string => {
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
        // Initial state
        isAuthenticated: false,
        user: null,
        tokenInfo: null,
        session: null,

        // Loading states
        isLoading: false,
        isLoggingIn: false,
        isRegistering: false,
        isResettingPassword: false,
        isRefreshingToken: false,

        // Error states
        error: null,
        loginError: null,
        registerError: null,
        passwordResetError: null,

        // Computed properties
        get isTokenExpired() {
          return isTokenExpired(get().tokenInfo);
        },
        get sessionTimeRemaining() {
          return getSessionTimeRemaining(get().session);
        },
        get userDisplayName() {
          return getUserDisplayName(get().user);
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
            const now = getCurrentTimestamp();
            const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(); // 24 hours

            const mockUser: User = {
              id: generateId(),
              email: credentials.email,
              displayName: credentials.email.split("@")[0],
              isEmailVerified: true,
              createdAt: now,
              updatedAt: now,
            };

            const mockTokenInfo: TokenInfo = {
              accessToken: `mock_token_${generateId()}`,
              refreshToken: `mock_refresh_${generateId()}`,
              expiresAt,
              tokenType: "Bearer",
            };

            const mockSession: Session = {
              id: generateId(),
              userId: mockUser.id,
              createdAt: now,
              lastActivity: now,
              expiresAt,
            };

            set({
              isAuthenticated: true,
              user: mockUser,
              tokenInfo: mockTokenInfo,
              session: mockSession,
              isLoggingIn: false,
              loginError: null,
            });

            return true;
          } catch (error) {
            const message = error instanceof Error ? error.message : "Login failed";
            set({
              isLoggingIn: false,
              loginError: message,
              isAuthenticated: false,
              user: null,
              tokenInfo: null,
              session: null,
            });
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
            const now = getCurrentTimestamp();

            const mockUser: User = {
              id: generateId(),
              email: credentials.email,
              firstName: credentials.firstName,
              lastName: credentials.lastName,
              displayName: credentials.firstName
                ? `${credentials.firstName} ${credentials.lastName || ""}`.trim()
                : credentials.email.split("@")[0],
              isEmailVerified: false, // Requires email verification
              createdAt: now,
              updatedAt: now,
            };

            set({
              user: mockUser,
              isRegistering: false,
              registerError: null,
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

        logout: async () => {
          set({ isLoading: true });

          try {
            // Mock API call to invalidate token
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              isAuthenticated: false,
              user: null,
              tokenInfo: null,
              session: null,
              isLoading: false,
              error: null,
              loginError: null,
              registerError: null,
              passwordResetError: null,
            });
          } catch (error) {
            // Even if logout fails on server, clear local state
            set({
              isAuthenticated: false,
              user: null,
              tokenInfo: null,
              session: null,
              isLoading: false,
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
            set({ isLoading: false, error: message });
          }
        },

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
            set({ isLoading: false, error: message });
            return false;
          }
        },

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
              accessToken: `mock_token_${generateId()}`,
              expiresAt: newExpiresAt,
            };

            set({
              tokenInfo: newTokenInfo,
              isRefreshingToken: false,
            });

            return true;
          } catch (error) {
            set({ isRefreshingToken: false });
            await get().logout();
            return false;
          }
        },

        validateToken: async () => {
          const { tokenInfo } = get();

          if (!tokenInfo || isTokenExpired(tokenInfo)) {
            return await get().refreshToken();
          }

          try {
            // Mock API call to validate token
            await new Promise((resolve) => setTimeout(resolve, 200));
            return true;
          } catch (error) {
            return await get().refreshToken();
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
              updatedAt: getCurrentTimestamp(),
            };
            const result = UserSchema.safeParse(updatedUser);

            if (!result.success) {
              throw new Error("Invalid user data");
            }

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({
              user: result.data,
              isLoading: false,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "User update failed";
            set({ isLoading: false, error: message });
            return false;
          }
        },

        updatePreferences: async (preferences) => {
          const { user } = get();
          if (!user) return false;

          set({ isLoading: true });

          try {
            const result = UserPreferencesSchema.safeParse(preferences);
            if (!result.success) {
              throw new Error("Invalid preferences data");
            }

            const updatedUser = {
              ...user,
              preferences: {
                ...user.preferences,
                ...result.data,
              },
              updatedAt: getCurrentTimestamp(),
            };

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            set({
              user: updatedUser,
              isLoading: false,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Preferences update failed";
            set({ isLoading: false, error: message });
            return false;
          }
        },

        updateSecurity: async (security) => {
          const { user } = get();
          if (!user) return false;

          set({ isLoading: true });

          try {
            const result = UserSecuritySchema.safeParse(security);
            if (!result.success) {
              throw new Error("Invalid security data");
            }

            const updatedUser = {
              ...user,
              security: {
                ...user.security,
                ...result.data,
              },
              updatedAt: getCurrentTimestamp(),
            };

            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({
              user: updatedUser,
              isLoading: false,
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Security update failed";
            set({ isLoading: false, error: message });
            return false;
          }
        },

        verifyEmail: async (token) => {
          set({ isLoading: true });

          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            const { user } = get();
            if (user) {
              set({
                user: {
                  ...user,
                  isEmailVerified: true,
                  updatedAt: getCurrentTimestamp(),
                },
                isLoading: false,
              });
            }

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Email verification failed";
            set({ isLoading: false, error: message });
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
            set({ isLoading: false, error: message });
            return false;
          }
        },

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
                lastActivity: getCurrentTimestamp(),
                expiresAt: newExpiresAt,
              },
            });

            return true;
          } catch (error) {
            return false;
          }
        },

        getActiveSessions: async () => {
          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            // Return mock sessions
            return [];
          } catch (error) {
            return [];
          }
        },

        revokeSession: async (sessionId) => {
          try {
            // Mock API call
            await new Promise((resolve) => setTimeout(resolve, 500));

            return true;
          } catch (error) {
            return false;
          }
        },

        // Utility actions
        clearErrors: () => {
          set({
            error: null,
            loginError: null,
            registerError: null,
            passwordResetError: null,
          });
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

        setUser: (user) => {
          set({ user });
        },

        initialize: async () => {
          const { tokenInfo, validateToken } = get();

          if (tokenInfo && !isTokenExpired(tokenInfo)) {
            set({ isAuthenticated: true });
            await validateToken();
          } else {
            await get().logout();
          }
        },
      }),
      {
        name: "auth-storage",
        partialize: (state) => ({
          // Persist user and token info, but not sensitive session data
          user: state.user,
          tokenInfo: state.tokenInfo,
          isAuthenticated: state.isAuthenticated,
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
    user: state.user,
    isLoading: state.isLoading,
    login: state.login,
    logout: state.logout,
    register: state.register,
  }));

export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
// Removed useUserDisplayName - now only exported from user-store.ts
export const useIsTokenExpired = () =>
  useAuthStore((state) => isTokenExpired(state.tokenInfo));
export const useSessionTimeRemaining = () =>
  useAuthStore((state) => getSessionTimeRemaining(state.session));
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
    registerError: state.registerError,
    passwordResetError: state.passwordResetError,
  }));
