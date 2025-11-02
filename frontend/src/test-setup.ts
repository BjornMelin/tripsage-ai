/**
 * @fileoverview Vitest global setup for the TripSage frontend.
 * Configures environment-wide mocks, testing-library cleanup, and helper wiring
 * to keep unit and integration tests deterministic and isolated.
 */

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import "@testing-library/jest-dom";
import { createMockSupabaseClient } from "./test/mock-helpers";

type UnknownRecord = Record<string, unknown>;

/**
 * Mock implementation for toast helpers.
 * @param _props Optional toast properties that are ignored by the mock.
 * @returns A toast handle containing dismiss and update spies.
 */
const mockToast = vi.fn((_props?: UnknownRecord) => ({
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

vi.mock("zustand/middleware", () => ({
  persist: <T>(fn: T) => fn,
  devtools: <T>(fn: T) => fn,
  subscribeWithSelector: <T>(fn: T) => fn,
  combine: <T>(fn: T) => fn,
}));

const mockSupabase = createMockSupabaseClient();
vi.mock("@/lib/supabase/client", () => ({
  useSupabase: () => mockSupabase,
  getBrowserClient: () => mockSupabase,
  createClient: () => mockSupabase,
}));

vi.mock("next/navigation", () => {
  const push = vi.fn();
  const replace = vi.fn();
  const refresh = vi.fn();
  const back = vi.fn();
  const forward = vi.fn();
  const prefetch = vi.fn();

  return {
    useRouter: () => ({ push, replace, refresh, back, forward, prefetch }),
    usePathname: () => "/",
    useSearchParams: () => new URLSearchParams(),
  };
});

/**
 * Create a mock MediaQueryList implementation for responsive tests.
 * @param defaultMatches Whether the media query should report a match by default.
 * @returns A function producing MediaQueryList mocks.
 */
const createMatchMediaMock =
  (defaultMatches = false) =>
  (query: string): MediaQueryList => ({
    matches: query === "(prefers-color-scheme: dark)" ? defaultMatches : false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });

/**
 * Build a mock Storage implementation backed by a Map.
 * @returns A Storage-compatible mock object.
 */
const createMockStorage = (): Storage => {
  const store = new Map<string, string>();

  return {
    get length() {
      return store.size;
    },
    clear: vi.fn(() => store.clear()),
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    key: vi.fn((index: number) => Array.from(store.keys())[index] ?? null),
    removeItem: vi.fn((key: string) => {
      store.delete(key);
    }),
    setItem: vi.fn((key: string, value: string) => {
      store.set(key, value);
    }),
  };
};

class MockResizeObserver implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin = "";
  readonly thresholds: number[] = [];

  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

if (typeof window !== "undefined") {
  const windowRef = globalThis.window as Window & typeof globalThis;

  Object.defineProperty(windowRef, "location", {
    value: {
      href: "https://example.com",
      reload: vi.fn(),
    },
    writable: true,
  });

  Object.defineProperty(windowRef, "navigator", {
    value: {
      userAgent: "Vitest",
    },
    writable: true,
  });

  Object.defineProperty(windowRef, "matchMedia", {
    writable: true,
    configurable: true,
    value: createMatchMediaMock(false),
  });

  Object.defineProperty(windowRef, "localStorage", {
    value: createMockStorage(),
  });

  Object.defineProperty(windowRef, "sessionStorage", {
    value: createMockStorage(),
  });
}

(globalThis as { ResizeObserver: typeof ResizeObserver }).ResizeObserver =
  MockResizeObserver;
(
  globalThis as { IntersectionObserver: typeof IntersectionObserver }
).IntersectionObserver = MockIntersectionObserver;

(
  globalThis as { CSS?: { supports: (property: string, value?: string) => boolean } }
).CSS = {
  supports: vi.fn().mockReturnValue(false),
};

globalThis.fetch = vi.fn() as unknown as typeof fetch;

const consoleSpies: Console = {
  ...console,
  error: vi.fn(),
  warn: vi.fn(),
  log: vi.fn(),
  info: vi.fn(),
  debug: vi.fn(),
  trace: vi.fn(),
};

globalThis.console = consoleSpies;

if (typeof process !== "undefined" && process.env) {
  const originalEnv = process.env;
  process.env = new Proxy(originalEnv, {
    get(target, prop: string) {
      if (prop === "NODE_ENV" && !target.NODE_ENV) {
        return "test";
      }
      return Reflect.get(target, prop);
    },
    set(target, prop: string, value) {
      return Reflect.set(target, prop, value);
    },
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
