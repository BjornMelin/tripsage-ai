/**
 * ULTRATHINK Auth Testing Fixtures
 * Comprehensive, maintainable test fixtures for authentication testing
 * Provides real-world scenarios with zero flaky patterns
 */

import { vi } from "vitest";
import type { 
  User, 
  TokenInfo, 
  Session, 
  LoginCredentials, 
  RegisterCredentials 
} from "@/stores/auth-store";

// Test User Data Templates
export const createMockUser = (overrides: Partial<User> = {}): User => ({
  id: "test-user-123",
  email: "test@example.com",
  firstName: "Test",
  lastName: "User",
  displayName: "Test User",
  isEmailVerified: true,
  createdAt: "2024-01-01T00:00:00.000Z",
  updatedAt: "2024-01-01T00:00:00.000Z",
  ...overrides,
});

export const createMockTokenInfo = (overrides: Partial<TokenInfo> = {}): TokenInfo => ({
  accessToken: "mock-access-token-12345",
  refreshToken: "mock-refresh-token-67890",
  expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(), // 1 hour from now
  tokenType: "Bearer",
  ...overrides,
});

export const createMockSession = (overrides: Partial<Session> = {}): Session => ({
  id: "session-123",
  userId: "test-user-123",
  deviceInfo: {
    userAgent: "Mozilla/5.0 (Test Browser)",
    ipAddress: "127.0.0.1",
    deviceId: "device-123",
  },
  createdAt: "2024-01-01T00:00:00.000Z",
  lastActivity: new Date().toISOString(),
  expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24 hours from now
  ...overrides,
});

// Auth State Templates
export const createAuthenticatedState = () => ({
  isAuthenticated: true,
  user: createMockUser(),
  tokenInfo: createMockTokenInfo(),
  session: createMockSession(),
  isLoading: false,
  isLoggingIn: false,
  isRegistering: false,
  isResettingPassword: false,
  isRefreshingToken: false,
  error: null,
  loginError: null,
  registerError: null,
  passwordResetError: null,
  isTokenExpired: false,
  sessionTimeRemaining: 24 * 60 * 60 * 1000, // 24 hours
  userDisplayName: "Test User",
});

export const createUnauthenticatedState = () => ({
  isAuthenticated: false,
  user: null,
  tokenInfo: null,
  session: null,
  isLoading: false,
  isLoggingIn: false,
  isRegistering: false,
  isResettingPassword: false,
  isRefreshingToken: false,
  error: null,
  loginError: null,
  registerError: null,
  passwordResetError: null,
  isTokenExpired: true,
  sessionTimeRemaining: 0,
  userDisplayName: "",
});

export const createLoadingState = (loadingType: 'login' | 'register' | 'general' = 'general') => ({
  ...createUnauthenticatedState(),
  isLoading: loadingType === 'general',
  isLoggingIn: loadingType === 'login',
  isRegistering: loadingType === 'register',
});

export const createErrorState = (errorType: 'login' | 'register' | 'general', message: string) => {
  const state = createUnauthenticatedState();
  switch (errorType) {
    case 'login':
      return { ...state, loginError: message };
    case 'register':
      return { ...state, registerError: message };
    case 'general':
      return { ...state, error: message };
  }
};

// Mock Function Templates
export const createMockAuthActions = () => ({
  login: vi.fn().mockResolvedValue(true),
  register: vi.fn().mockResolvedValue(true),
  logout: vi.fn().mockResolvedValue(undefined),
  logoutAllDevices: vi.fn().mockResolvedValue(undefined),
  requestPasswordReset: vi.fn().mockResolvedValue(true),
  resetPassword: vi.fn().mockResolvedValue(true),
  changePassword: vi.fn().mockResolvedValue(true),
  refreshToken: vi.fn().mockResolvedValue(true),
  validateToken: vi.fn().mockResolvedValue(true),
  updateUser: vi.fn().mockResolvedValue(true),
  updatePreferences: vi.fn().mockResolvedValue(true),
  updateSecurity: vi.fn().mockResolvedValue(true),
  verifyEmail: vi.fn().mockResolvedValue(true),
  resendEmailVerification: vi.fn().mockResolvedValue(true),
  extendSession: vi.fn().mockResolvedValue(true),
  getActiveSessions: vi.fn().mockResolvedValue([]),
  revokeSession: vi.fn().mockResolvedValue(true),
  clearErrors: vi.fn(),
  clearError: vi.fn(),
  setUser: vi.fn(),
  initialize: vi.fn().mockResolvedValue(undefined),
});

export const createMockErrorActions = () => ({
  clearErrors: vi.fn(),
  clearError: vi.fn(),
});

// Test Credentials
export const validLoginCredentials: LoginCredentials = {
  email: "test@example.com",
  password: "SecurePassword123!",
  rememberMe: false,
};

export const validRegisterCredentials: RegisterCredentials = {
  email: "newuser@example.com",
  password: "SecurePassword123!",
  confirmPassword: "SecurePassword123!",
  firstName: "New",
  lastName: "User",
  acceptTerms: true,
};

export const invalidCredentials = {
  emptyEmail: { email: "", password: "password123" },
  emptyPassword: { email: "test@example.com", password: "" },
  invalidEmail: { email: "invalid-email", password: "password123" },
  weakPassword: { email: "test@example.com", password: "weak" },
  mismatchedPasswords: {
    ...validRegisterCredentials,
    confirmPassword: "DifferentPassword123!",
  },
  termsNotAccepted: {
    ...validRegisterCredentials,
    acceptTerms: false,
  },
};

// Mock API Response Templates
export const createMockApiResponse = (data: any, ok = true, status = 200) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
  text: vi.fn().mockResolvedValue(JSON.stringify(data)),
});

export const mockAuthApiResponse = {
  success: createMockApiResponse({
    user: createMockUser(),
    tokenInfo: createMockTokenInfo(),
    session: createMockSession(),
  }),
  unauthorized: createMockApiResponse(
    { error: "Invalid credentials" },
    false,
    401
  ),
  serverError: createMockApiResponse(
    { error: "Internal server error" },
    false,
    500
  ),
  validationError: createMockApiResponse(
    { error: "Email and password are required" },
    false,
    400
  ),
};

// Router Mock Helper
export const createMockRouter = () => ({
  push: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
});

// Complete Auth Store Mock Factory
export const createMockAuthStore = (initialState = createUnauthenticatedState()) => {
  const actions = createMockAuthActions();
  const errorActions = createMockErrorActions();
  
  return {
    ...initialState,
    ...actions,
    ...errorActions,
  };
};

// Common Test Scenarios
export const authTestScenarios = {
  authenticated: {
    state: createAuthenticatedState(),
    description: "User is logged in with valid session",
  },
  unauthenticated: {
    state: createUnauthenticatedState(),
    description: "User is not logged in",
  },
  loggingIn: {
    state: createLoadingState('login'),
    description: "User is in the process of logging in",
  },
  registering: {
    state: createLoadingState('register'),
    description: "User is in the process of registering",
  },
  loginError: {
    state: createErrorState('login', 'Invalid email or password'),
    description: "Login failed with error message",
  },
  registerError: {
    state: createErrorState('register', 'Email already exists'),
    description: "Registration failed with error message",
  },
  expiredToken: {
    state: {
      ...createAuthenticatedState(),
      isTokenExpired: true,
      tokenInfo: createMockTokenInfo({
        expiresAt: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1 hour ago
      }),
    },
    description: "User has expired token",
  },
};

// Environment Mock Helpers
export const mockDevelopmentEnv = () => {
  vi.stubEnv("NODE_ENV", "development");
};

export const mockProductionEnv = () => {
  vi.stubEnv("NODE_ENV", "production");
};

// Cleanup Helpers
export const restoreEnv = () => {
  vi.unstubAllEnvs();
};

export const restoreAllMocks = () => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
  restoreEnv();
};

// Async Test Helpers
export const waitForAuthAction = async (mockFn: any, timeout = 1000) => {
  const start = Date.now();
  while (!mockFn.mock.calls.length && Date.now() - start < timeout) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  return mockFn.mock.calls.length > 0;
};

// Form Input Helpers
export const createFormInputData = (overrides: Record<string, string> = {}) => ({
  email: "test@example.com",
  password: "SecurePassword123!",
  fullName: "Test User",
  ...overrides,
});

export const createPasswordStrengthScenarios = () => ({
  weak: "1",
  fair: "abc",
  good: "abcdefgh",
  strong: "StrongPassword123!@",
});