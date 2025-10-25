/**
 * @fileoverview Small DOM-agnostic utilities for formatting and timing.
 * All helpers are pure and safe for both server and browser runtimes.
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

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
  const date = new Date(input);
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
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
    style: "currency",
    currency,
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
export function debounce<T extends (...args: any[]) => any>(
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
export function throttle<T extends (...args: any[]) => any>(
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
