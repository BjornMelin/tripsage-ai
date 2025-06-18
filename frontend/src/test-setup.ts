import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll, vi } from "vitest";
import "@testing-library/jest-dom";

// Mock useToast hook BEFORE anything else
const mockToast = vi.fn((props: any) => ({
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

// Mock zustand middleware
vi.mock("zustand/middleware", () => ({
  persist: vi.fn((fn: unknown) => fn),
  devtools: vi.fn((fn: unknown) => fn),
  subscribeWithSelector: vi.fn((fn: unknown) => fn),
  combine: vi.fn((fn: unknown) => fn),
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
global.renderWithProviders = testUtils.renderWithProviders;

// Mock environment variables for testing
// Create a proxy for process.env to avoid descriptor errors
if (typeof process !== 'undefined' && process.env) {
  const originalEnv = process.env;
  process.env = new Proxy(originalEnv, {
    get(target, prop) {
      if (prop === 'NODE_ENV' && !target.NODE_ENV) {
        return 'test';
      }
      return target[prop as string];
    },
    set(target, prop, value) {
      target[prop as string] = value;
      return true;
    }
  });
}
