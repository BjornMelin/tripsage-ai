/**
 * @fileoverview Shared test utilities and helpers for auth slice tests.
 */

import { act } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import type { AuthUser } from "@/lib/schemas/stores";
import { useAuthCore } from "@/stores/auth/auth-core";
import { useAuthSession } from "@/stores/auth/auth-session";
import { useAuthValidation } from "@/stores/auth/auth-validation";

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
 * Resets all auth slices to their initial state.
 */
export const resetAuthSlices = (): void => {
  act(() => {
    // Reset auth-core slice
    useAuthCore.setState({
      error: null,
      isAuthenticated: false,
      isLoading: false,
      isLoggingIn: false,
      isRegistering: false,
      user: null,
      userDisplayName: "",
    });

    // Reset auth-session slice
    useAuthSession.setState({
      isRefreshingToken: false,
      session: null,
      tokenInfo: null,
    });

    // Reset auth-validation slice
    useAuthValidation.setState({
      isResettingPassword: false,
      isVerifyingEmail: false,
      passwordResetError: null,
      registerError: null,
    });
  });
};

/**
 * Creates a mock user with optional overrides.
 *
 * @param overrides - Partial user to override defaults
 * @returns A complete user object
 */
export const createMockUser = (overrides: Partial<AuthUser> = {}): AuthUser => {
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
 * Sets up beforeEach and afterEach hooks for auth slice tests.
 * Includes timeout mocking and slice reset.
 */
export const setupAuthSliceTests = (): void => {
  let timeoutSpy: { mockRestore: () => void } | null = null;

  beforeEach(() => {
    timeoutSpy = setupTimeoutMock();
    resetAuthSlices();
  });

  afterEach(() => {
    timeoutSpy?.mockRestore();
  });
};
