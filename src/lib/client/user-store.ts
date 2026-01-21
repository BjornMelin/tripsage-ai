/**
 * @fileoverview Client-only helpers for reading user context from the global user store.
 */

"use client";

declare global {
  interface Window {
    userStore?: {
      user?: {
        id?: string;
      };
    };
  }
}

/**
 * Safely reads the current user ID from `window.userStore` if available.
 *
 * The global is initialized by the auth store during app bootstrap. This helper is
 * defensive to avoid throwing in SSR, early hydration, or privacy-restricted contexts.
 */
export function getUserIdFromUserStore(): string | undefined {
  try {
    return window.userStore?.user?.id;
  } catch {
    return undefined;
  }
}
