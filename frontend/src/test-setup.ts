/**
 * @fileoverview Vitest global setup for the TripSage frontend.
 * Configures environment-wide mocks, testing-library cleanup, and helper wiring
 * to keep unit and integration tests deterministic and isolated.
 */

import { cleanup } from "@testing-library/react";
import React from "react";
import { afterEach, vi } from "vitest";
import "@testing-library/jest-dom";
import {
  ReadableStream as NodeReadableStream,
  TransformStream as NodeTransformStream,
  WritableStream as NodeWritableStream,
} from "node:stream/web";
import { createMockSupabaseClient } from "./test/mock-helpers";
import { resetTestQueryClient } from "./test/test-utils";

type UnknownRecord = Record<string, unknown>;

/**
 * Mock implementation for toast helpers.
 * @param _props Optional toast properties that are ignored by the mock.
 * @returns A toast handle containing dismiss and update spies.
 */
const MOCK_TOAST = vi.fn((_props?: UnknownRecord) => ({
  dismiss: vi.fn(),
  id: `toast-${Date.now()}`,
  update: vi.fn(),
}));

vi.mock("@/components/ui/use-toast", () => ({
  toast: MOCK_TOAST,
  useToast: vi.fn(() => ({
    dismiss: vi.fn(),
    toast: MOCK_TOAST,
    toasts: [],
  })),
}));

vi.mock("zustand/middleware", () => ({
  combine: <T>(fn: T) => fn,
  devtools: <T>(fn: T) => fn,
  persist: <T>(fn: T) => fn,
  subscribeWithSelector: <T>(fn: T) => fn,
}));

const MOCK_SUPABASE = createMockSupabaseClient();
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => MOCK_SUPABASE,
  getBrowserClient: () => MOCK_SUPABASE,
  useSupabase: () => MOCK_SUPABASE,
}));

vi.mock("next/navigation", () => {
  const push = vi.fn();
  const replace = vi.fn();
  const refresh = vi.fn();
  const back = vi.fn();
  const forward = vi.fn();
  const prefetch = vi.fn();

  return {
    usePathname: () => "/",
    useRouter: () => ({ back, forward, prefetch, push, refresh, replace }),
    useSearchParams: () => new URLSearchParams(),
  };
});

// Simplify Next/Image for tests to avoid overhead and ESM/DOM quirks
vi.mock("next/image", () => {
  return {
    default: (props: Record<string, unknown> & { src?: string; alt?: string }) => {
      const { src, alt, ...rest } = props ?? {};
      return React.createElement("img", {
        alt: alt ?? "",
        src: typeof src === "string" ? src : "",
        ...rest,
      } as Record<string, unknown>);
    },
  };
});

/**
 * Create a mock MediaQueryList implementation for responsive tests.
 * @param defaultMatches Whether the media query should report a match by default.
 * @returns A function producing MediaQueryList mocks.
 */
const CREATE_MATCH_MEDIA_MOCK =
  (defaultMatches = false) =>
  (query: string): MediaQueryList => ({
    addEventListener: vi.fn(),
    addListener: vi.fn(),
    dispatchEvent: vi.fn(),
    matches: query === "(prefers-color-scheme: dark)" ? defaultMatches : false,
    media: query,
    onchange: null,
    removeEventListener: vi.fn(),
    removeListener: vi.fn(),
  });

/**
 * Build a mock Storage implementation backed by a Map.
 * @returns A Storage-compatible mock object.
 */
const CREATE_MOCK_STORAGE = (): Storage => {
  const store = new Map<string, string>();

  return {
    clear: vi.fn(() => store.clear()),
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    key: vi.fn((index: number) => Array.from(store.keys())[index] ?? null),
    get length() {
      return store.size;
    },
    removeItem: vi.fn((key: string) => {
      store.delete(key);
    }),
    setItem: vi.fn((key: string, value: string) => {
      store.set(key, value);
    }),
  };
};

class MockResizeObserver implements ResizeObserver {
  observe(): void {
    // Mock implementation - no-op
  }
  unobserve(): void {
    // Mock implementation - no-op
  }
  disconnect(): void {
    // Mock implementation - no-op
  }
}

class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin = "";
  readonly thresholds: number[] = [];

  observe(): void {
    // Mock implementation - no-op
  }
  unobserve(): void {
    // Mock implementation - no-op
  }
  disconnect(): void {
    // Mock implementation - no-op
  }
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

/**
 * Helper constant to check if we're in a JSDOM environment.
 * Used to conditionally apply window-specific mocks.
 */
const IS_JSDOM_ENVIRONMENT = typeof window !== "undefined";

if (IS_JSDOM_ENVIRONMENT) {
  const WINDOW_REF = globalThis.window as Window & typeof globalThis;

  // Use JSDOM default location; avoid redefining to prevent errors in vmThreads

  Object.defineProperty(WINDOW_REF, "navigator", {
    value: {
      userAgent: "Vitest",
    },
    writable: true,
  });

  Object.defineProperty(WINDOW_REF, "matchMedia", {
    configurable: true,
    value: CREATE_MATCH_MEDIA_MOCK(false),
    writable: true,
  });

  Object.defineProperty(WINDOW_REF, "localStorage", {
    value: CREATE_MOCK_STORAGE(),
  });

  Object.defineProperty(WINDOW_REF, "sessionStorage", {
    value: CREATE_MOCK_STORAGE(),
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

// Only provide a global fetch mock in JSDOM, where window is available.
if (IS_JSDOM_ENVIRONMENT) {
  globalThis.fetch = vi.fn() as unknown as typeof fetch;
}

// Provide Web Streams polyfills for environments missing them (used by
// eventsource-parser / AI SDK transport in tests)
type RS = typeof ReadableStream;
type WS = typeof WritableStream;
type TS = typeof TransformStream;
const GLOBAL_STREAMS = globalThis as typeof globalThis & {
  ReadableStream?: RS;
  WritableStream?: WS;
  TransformStream?: TS;
};
if (!GLOBAL_STREAMS.ReadableStream) {
  (GLOBAL_STREAMS as { ReadableStream?: RS }).ReadableStream =
    NodeReadableStream as unknown as RS;
}
if (!GLOBAL_STREAMS.WritableStream) {
  (GLOBAL_STREAMS as { WritableStream?: WS }).WritableStream =
    NodeWritableStream as unknown as WS;
}
if (!GLOBAL_STREAMS.TransformStream) {
  (GLOBAL_STREAMS as { TransformStream?: TS }).TransformStream =
    NodeTransformStream as unknown as TS;
}

// Console is NOT mocked globally to allow real errors to surface during testing.
// Tests that expect specific console output should use vi.spyOn(console, "error")
// locally and restore it after the test.

if (typeof process !== "undefined" && process.env) {
  const ORIGINAL_ENV = process.env;
  process.env = new Proxy(ORIGINAL_ENV, {
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
  resetTestQueryClient();
  vi.restoreAllMocks();
});

// Timers are configured per-suite in store tests when needed.
