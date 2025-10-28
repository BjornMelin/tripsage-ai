/**
 * @fileoverview Vitest global test setup configuration.
 *
 * Global test configuration and setup for the TripSage frontend test suite.
 * Configures Vitest environment with comprehensive mocks, cleanup utilities,
 * and shared test infrastructure for consistent and reliable testing across
 * React components, hooks, and integration tests.
 */

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import "@testing-library/jest-dom";

/**
 * Mock toast function for testing toast notifications.
 *
 * Creates a mock implementation of the toast function that generates unique IDs
 * and provides mock dismiss/update methods for testing toast behavior without
 * actual UI rendering.
 *
 * @param _props - Toast properties (unused in mock)
 * @returns Mock toast object with id and control methods
 */
const mockToast = vi.fn((_props: any) => ({
  id: `toast-${Date.now()}`,
  dismiss: vi.fn(),
  update: vi.fn(),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: vi.fn(() => ({
    toast: mockToast,
    dismiss: vi.fn(),
    toasts: [],
  })),
  toast: mockToast,
}));

// Setup Supabase mocks before any tests run
import "./test/setup-supabase-mocks";

// Mock zustand middleware - preserve store functionality
vi.mock("zustand/middleware", () => ({
  persist: (fn: any, _config?: any) => fn,
  devtools: (fn: any, _config?: any) => fn,
  subscribeWithSelector: (fn: any) => fn,
  combine: (fn: any) => fn,
}));

// Clean up after each test
afterEach(() => {
  cleanup();
});

// Also restore all spies/stubs between tests to avoid cross-test pollution.
afterEach(() => {
  vi.restoreAllMocks();
});

// Mock window.location
Object.defineProperty(window, "location", {
  value: {
    href: "https://example.com",
    reload: vi.fn(),
  },
  writable: true,
});

// Mock navigator
Object.defineProperty(window, "navigator", {
  value: {
    userAgent: "Test User Agent",
  },
  writable: true,
});

/**
 * Creates a mock implementation of the window.matchMedia API.
 *
 * Provides a mock matchMedia function for testing responsive design and theme
 * detection logic. Specifically handles dark mode preference queries while
 * defaulting to false for other media queries.
 *
 * @param defaultMatches - Default value for dark mode preference queries
 * @returns Mock matchMedia function that returns MediaQueryList-like objects
 */
const createMatchMediaMock = (defaultMatches = false) =>
  vi.fn().mockImplementation((query: string) => ({
    matches: query === "(prefers-color-scheme: dark)" ? defaultMatches : false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

// Ensure matchMedia is available immediately
(globalThis as any).window = globalThis.window ?? {};
Object.defineProperty(globalThis.window, "matchMedia", {
  writable: true,
  configurable: true,
  value: createMatchMediaMock(false),
});

// ResizeObserver mock (used by charts, virtualized lists, etc.)
// Matches minimal API surface to keep tests deterministic.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// IntersectionObserver mock
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).IntersectionObserver = class IntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  /** Return an empty set of entries for tests */
  takeRecords(): unknown[] { return []; }
  /** Root element (unused in tests) */
  root: unknown = null;
  /** Root margin (unused in tests) */
  rootMargin = "";
  /** Thresholds (unused in tests) */
  thresholds: number[] = [];
};

// CSS.supports mock for components checking feature support
Object.defineProperty(global, "CSS", {
  value: {
    supports: vi.fn().mockReturnValue(false),
  },
});

/**
 * Mock storage implementation for localStorage and sessionStorage.
 *
 * Provides a mock Storage API implementation with Vitest spies for testing
 * components that interact with browser storage APIs without affecting
 * actual browser state.
 */
const mockStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

Object.defineProperty(window, "localStorage", {
  value: mockStorage,
});

Object.defineProperty(window, "sessionStorage", {
  value: mockStorage,
});

// Mock fetch
global.fetch = vi.fn();

// Mock console methods for cleaner test output
global.console = {
  ...console,
  error: vi.fn(),
  warn: vi.fn(),
  log: vi.fn(),
  info: vi.fn(),
};

// Make test utils available globally
import * as testUtils from "./test/test-utils";

/**
 * Global type declarations for test utilities.
 *
 * Extends the global scope with test utility functions that are made available
 * to all test files for consistent testing setup and component rendering.
 */
declare global {
  /** Global test utility for rendering React components with all required providers */
  var renderWithProviders: typeof testUtils.renderWithProviders;
}

(globalThis as any).renderWithProviders = testUtils.renderWithProviders;

// Mock environment variables for testing
// Create a proxy for process.env to avoid descriptor errors
if (typeof process !== "undefined" && process.env) {
  const originalEnv = process.env;
  process.env = new Proxy(originalEnv, {
    get(target, prop) {
      if (prop === "NODE_ENV" && !target.NODE_ENV) {
        return "test";
      }
      return target[prop as string];
    },
    set(target, prop, value) {
      target[prop as string] = value;
      return true;
    },
  });
}
