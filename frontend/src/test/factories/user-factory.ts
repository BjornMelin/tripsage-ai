/**
 * @fileoverview Factory for creating User test data.
 */

import type { User } from "@supabase/supabase-js";

let userIdCounter = 1;

export interface UserOverrides {
  id?: string;
  email?: string;
  created_at?: string;
  app_metadata?: Record<string, unknown>;
  user_metadata?: Record<string, unknown>;
  aud?: string;
}

/**
 * Creates a mock User with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete User object
 */
export const createUser = (overrides: UserOverrides = {}): User => {
  const id = overrides.id ?? `user-${userIdCounter++}`;

  return {
    app_metadata: overrides.app_metadata ?? {},
    aud: overrides.aud ?? "authenticated",
    created_at: overrides.created_at ?? new Date().toISOString(),
    email: overrides.email ?? `user${id}@example.com`,
    id,
    user_metadata: overrides.user_metadata ?? {},
  } as User;
};

/**
 * Creates multiple users at once.
 *
 * @param count - Number of users to create
 * @param overridesFn - Optional function to customize each user (receives index)
 * @returns Array of User objects
 */
export const createUsers = (
  count: number,
  overridesFn?: (index: number) => UserOverrides
): User[] => {
  return Array.from({ length: count }, (_, i) =>
    createUser(overridesFn ? overridesFn(i) : {})
  );
};

/**
 * Resets the user ID counter for deterministic test data.
 * Call this in beforeEach() if you need consistent IDs across test runs.
 */
export const resetUserFactory = (): void => {
  userIdCounter = 1;
};
