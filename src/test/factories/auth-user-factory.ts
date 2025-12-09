/**
 * @fileoverview Factory for creating AuthUser test data.
 */

import type { AuthUser } from "@schemas/stores";

let authUserIdCounter = 1;

export interface AuthUserOverrides {
  id?: string;
  email?: string;
  displayName?: string;
  firstName?: string;
  lastName?: string;
  createdAt?: string;
  updatedAt?: string;
  isEmailVerified?: boolean;
  preferences?: AuthUser["preferences"];
}

/**
 * Creates a mock AuthUser with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete AuthUser object
 */
export const createAuthUser = (overrides: AuthUserOverrides = {}): AuthUser => {
  const id = overrides.id ?? `user-${authUserIdCounter++}`;

  return {
    createdAt: overrides.createdAt ?? "2025-01-01T00:00:00Z",
    displayName: "displayName" in overrides ? overrides.displayName : "Test User",
    email: overrides.email ?? `test${id}@example.com`,
    firstName: "firstName" in overrides ? overrides.firstName : "Test",
    id,
    isEmailVerified: overrides.isEmailVerified ?? true,
    lastName: "lastName" in overrides ? overrides.lastName : "User",
    preferences: overrides.preferences ?? {
      language: "en",
      theme: "light" as const,
      timezone: "UTC",
    },
    updatedAt: overrides.updatedAt ?? "2025-01-01T00:00:00Z",
  };
};

/**
 * Creates multiple AuthUsers at once.
 *
 * @param count - Number of users to create
 * @param overridesFn - Optional function to customize each user (receives index)
 * @returns Array of AuthUser objects
 */
export const createAuthUsers = (
  count: number,
  overridesFn?: (index: number) => AuthUserOverrides
): AuthUser[] => {
  return Array.from({ length: count }, (_, i) =>
    createAuthUser(overridesFn ? overridesFn(i) : {})
  );
};

/**
 * Resets the auth user ID counter for deterministic test data.
 * Call this in beforeEach() if you need consistent IDs across test runs.
 */
export const resetAuthUserFactory = (): void => {
  authUserIdCounter = 1;
};
