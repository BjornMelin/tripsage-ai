/**
 * @fileoverview Shared helper functions for Zustand stores.
 * Centralizes common patterns to avoid duplication across stores.
 */

import { nowIso, secureId } from "@/lib/security/random";

/**
 * Generate cryptographically secure ID.
 * @param length Desired length of the ID (default 12)
 * @returns A secure identifier string
 */
export const generateId = (length = 12): string => secureId(length);

/**
 * Get current timestamp in ISO format.
 * @returns ISO timestamp string
 */
export const getCurrentTimestamp = (): string => nowIso();

/**
 * Check if ISO timestamp is in the past (expired).
 * @param timestamp ISO timestamp string or null
 * @returns True if timestamp is null or in the past
 */
export const isExpired = (timestamp: string | null): boolean => {
  if (!timestamp) return true;
  return new Date() >= new Date(timestamp);
};

/**
 * Calculate milliseconds until timestamp.
 * @param timestamp ISO timestamp string or null
 * @returns Milliseconds until timestamp, or 0 if timestamp is null or in the past
 */
export const timeUntil = (timestamp: string | null): number => {
  if (!timestamp) return 0;
  const now = Date.now();
  const target = new Date(timestamp).getTime();
  return Math.max(0, target - now);
};

/**
 * Create display name from user object.
 * @param user User object with displayName, firstName, lastName, and email
 * @returns Display name string
 */
export const getDisplayName = (
  user: {
    displayName?: string;
    firstName?: string;
    lastName?: string;
    email: string;
  } | null
): string => {
  if (!user) return "";
  if (user.displayName) return user.displayName;
  if (user.firstName && user.lastName) {
    return `${user.firstName} ${user.lastName}`;
  }
  if (user.firstName) return user.firstName;
  return user.email.split("@")[0];
};
