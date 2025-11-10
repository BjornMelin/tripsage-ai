/**
 * @fileoverview Shared test utilities and helpers for auth store tests.
 */

import { act } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import type { User } from "@/stores/auth-store";
import { useAuthStore } from "@/stores/auth-store";

/**
 * Accelerates store async flows in test suites by mocking setTimeout.
 * Returns a cleanup function that should be called in afterEach.
 */
export const setupTimeoutMock = (): { mockRestore: () => void } => {
  const timeoutSpy = vi.spyOn(globalThis, "setTimeout").mockImplementation(((
    cb: TimerHandler,
    _ms?: number,
    ...args: unknown[]
  ) => {
    if (typeof cb === "function") {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      cb(...(args as never[]));
    }
    return 0 as unknown as ReturnType<typeof setTimeout>;
  }) as unknown as typeof setTimeout);

  return {
    mockRestore: () => {
      timeoutSpy.mockRestore();
    },
  };
};

/**
 * Resets the auth store to its initial state.
 */
export const resetAuthStore = (): void => {
  act(() => {
    useAuthStore.setState({
      error: null,
      isAuthenticated: false,
      isLoading: false,
      isLoggingIn: false,
      isRefreshingToken: false,
      isRegistering: false,
      isResettingPassword: false,
      loginError: null,
      passwordResetError: null,
      registerError: null,
      session: null,
      tokenInfo: null,
      user: null,
    });
  });
};

/**
 * Creates a mock user with optional overrides.
 *
 * @param overrides - Partial user to override defaults
 * @returns A complete user object
 */
export const createMockUser = (overrides: Partial<User> = {}): User => {
  return {
    avatarUrl: "https://example.com/avatar.jpg",
    bio: "Test bio",
    createdAt: "2025-01-01T00:00:00Z",
    displayName: "Custom Display Name",
    email: "test@example.com",
    firstName: "John",
    id: "user-1",
    isEmailVerified: true,
    lastName: "Doe",
    preferences: {
      language: "en",
      notifications: {
        email: true,
        marketing: false,
        priceAlerts: false,
        tripReminders: true,
      },
      theme: "light" as const,
      timezone: "UTC",
    },
    security: {
      lastPasswordChange: "2025-01-01T00:00:00Z",
      twoFactorEnabled: false,
    },
    updatedAt: "2025-01-01T00:00:00Z",
    ...overrides,
  };
};

/**
 * Sets up beforeEach and afterEach hooks for auth store tests.
 * Includes timeout mocking and store reset.
 */
export const setupAuthStoreTests = (): void => {
  let timeoutSpy: { mockRestore: () => void } | null = null;

  beforeEach(() => {
    timeoutSpy = setupTimeoutMock();
    resetAuthStore();
  });

  afterEach(() => {
    timeoutSpy?.mockRestore();
  });
};
