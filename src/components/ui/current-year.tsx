"use client";

/**
 * Displays the current year on the client to avoid server prerender time coupling.
 */
export function CurrentYear() {
  return <>{new Date().getFullYear()}</>;
}
