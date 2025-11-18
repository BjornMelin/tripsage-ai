/**
 * @fileoverview Small DOM-agnostic utilities for formatting and timing.
 * All helpers are pure and safe for both server and browser runtimes.
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { secureUuid } from "@/lib/security/random";

/**
 * Compose Tailwind class strings with conflict resolution.
 *
 * @param inputs Class tokens and conditional fragments.
 * @returns Merged className string.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date-like value as a long US date (e.g., January 1, 2025).
 *
 * @param input Date instance, timestamp, or ISO string.
 * @returns Human-readable date string.
 */
export function formatDate(input: string | number | Date): string {
  let date: Date;
  if (input instanceof Date) {
    date = input;
  } else if (typeof input === "number") {
    date = new Date(input);
  } else {
    date = DateUtils.parse(input);
  }
  return DateUtils.format(date, "MMMM d, yyyy");
}

/**
 * Test if a string is a syntactically valid URL.
 *
 * @param url Candidate URL string.
 * @returns True when `new URL(url)` succeeds.
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch (_error) {
    return false;
  }
}

/**
 * Truncate a string and append an ellipsis when exceeded.
 *
 * @param str Source string.
 * @param length Maximum length before truncation.
 * @returns Original string or truncated with `...`.
 */
export function truncate(str: string, length: number): string {
  if (str.length <= length) {
    return str;
  }

  return `${str.slice(0, length)}...`;
}

/**
 * Format a number as currency in the en-US locale.
 *
 * @param amount Numeric amount.
 * @param currency ISO 4217 code (default: `USD`).
 * @returns Formatted currency string.
 */
export function formatCurrency(amount: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    currency,
    style: "currency",
  }).format(amount);
}

/**
 * Return a debounced function that postpones invocation until after `delay`.
 *
 * @typeParam T Callable type.
 * @param fn Target function to debounce.
 * @param delay Delay in milliseconds.
 * @returns Debounced function.
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;

  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Return a throttled function that invokes at most once per `delay` window.
 *
 * @typeParam T Callable type.
 * @param fn Target function to throttle.
 * @param delay Minimum interval in milliseconds between calls.
 * @returns Throttled function.
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0;

  return (...args: Parameters<T>) => {
    const now = Date.now();

    if (now - lastCall < delay) {
      return;
    }

    lastCall = now;
    return fn(...args);
  };
}

/**
 * Execute a promise without awaiting while observing rejections.
 *
 * @param promise Promise to execute in fire-and-forget mode.
 * @param onError Optional handler when the promise rejects.
 */
export function fireAndForget<T>(
  promise: Promise<T>,
  onError?: (error: unknown) => void
): void {
  const handleRejection = (error: unknown) => {
    if (onError) {
      onError(error);
      return;
    }

    if (process.env.NODE_ENV !== "test") {
      console.warn("[fireAndForget] swallowed rejection", error);
    }
  };

  Promise.resolve(promise).catch(handleRejection);
}

/**
 * Get or create a per-session identifier for error tracking and telemetry.
 *
 * The ID is stored in `sessionStorage` under the key `session_id`. If it does
 * not exist, a new ID is generated using `secureUuid()` and persisted. When
 * called in environments without access to `sessionStorage` (e.g., server
 * rendering, certain privacy contexts), the function returns `undefined`.
 *
 * @returns A stable session identifier string or `undefined` when unavailable.
 */
export function getSessionId(): string | undefined {
  try {
    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = `session_${secureUuid()}`;
      sessionStorage.setItem("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return undefined;
  }
}
