/**
 * @fileoverview MediaQueryList mock factory for responsive design tests.
 * Use this instead of global mocks to improve test boot time.
 *
 * Usage:
 *   import { createMockMatchMedia } from "@/test/mocks/media-query";
 *
 *   it("should respond to dark mode", () => {
 *     const matchMedia = createMockMatchMedia({ "(prefers-color-scheme: dark)": true });
 *     window.matchMedia = matchMedia;
 *     // ... test code
 *   });
 */

import { vi } from "vitest";

export interface MediaQueryConfig {
  [query: string]: boolean;
}

/**
 * Creates a mock MediaQueryList for a specific query.
 *
 * @param query - The media query string
 * @param matches - Whether the query matches
 * @returns A MediaQueryList-compatible mock
 */
export const createMockMediaQueryList = (
  query: string,
  matches: boolean
): MediaQueryList => ({
  addEventListener: vi.fn(),
  addListener: vi.fn(),
  dispatchEvent: vi.fn(),
  matches,
  media: query,
  onchange: null,
  removeEventListener: vi.fn(),
  removeListener: vi.fn(),
});

/**
 * Creates a mock matchMedia function that responds to configured queries.
 *
 * @param config - Map of query strings to match results
 * @param defaultMatches - Default result for unconfigured queries
 * @returns A matchMedia-compatible function
 *
 * @example
 * const matchMedia = createMockMatchMedia({
 *   "(prefers-color-scheme: dark)": true,
 *   "(min-width: 768px)": false,
 * });
 * window.matchMedia = matchMedia;
 */
export const createMockMatchMedia = (
  config: MediaQueryConfig = {},
  defaultMatches = false
): ((query: string) => MediaQueryList) => {
  return (query: string): MediaQueryList => {
    const matches = config[query] ?? defaultMatches;
    return createMockMediaQueryList(query, matches);
  };
};

/**
 * Installs a mock matchMedia on window for tests.
 *
 * @param config - Media query configuration
 * @returns The mock matchMedia function
 *
 * @example
 * beforeEach(() => {
 *   installMockMatchMedia({ "(prefers-color-scheme: dark)": true });
 * });
 */
export const installMockMatchMedia = (
  config: MediaQueryConfig = {}
): ((query: string) => MediaQueryList) => {
  const mockMatchMedia = createMockMatchMedia(config);
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: mockMatchMedia,
    writable: true,
  });
  return mockMatchMedia;
};
