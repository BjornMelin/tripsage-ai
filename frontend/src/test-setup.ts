import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll, vi } from "vitest";
import "@testing-library/jest-dom";

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

// Mock environment variables for testing
if (!process.env.NODE_ENV) {
  Object.defineProperty(process.env, "NODE_ENV", {
    value: "test",
    writable: true,
    configurable: true,
  });
}
