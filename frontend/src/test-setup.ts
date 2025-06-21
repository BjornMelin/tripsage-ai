import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import "@testing-library/jest-dom";

// Mock useToast hook BEFORE anything else
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

// Mock window.matchMedia for theme detection - ensure global consistency
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

// Mock storage
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

// Type-safe global assignment
declare global {
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
