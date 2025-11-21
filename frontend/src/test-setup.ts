/**
 * @fileoverview Vitest global setup for the TripSage frontend.
 * Provides essential platform polyfills, DOM APIs, and minimal Next.js mocks.
 * Feature-specific mocks (React Query, AI SDK, Supabase) should be imported
 * from @/test/mocks/* in individual test files.
 */

import { cleanup } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, vi } from "vitest";
import "@testing-library/jest-dom";
import {
  ReadableStream as NodeReadableStream,
  TransformStream as NodeTransformStream,
  WritableStream as NodeWritableStream,
} from "node:stream/web";
import { resetTestQueryClient } from "./test/test-utils";

(
  globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

// Minimal toast mock (used by many components)
type UnknownRecord = Record<string, unknown>;
const MOCK_TOAST = vi.fn((_props?: UnknownRecord) => ({
  dismiss: vi.fn(),
  id: `toast-${Date.now()}`,
  update: vi.fn(),
}));

const LOCATION_ORIGIN = "http://localhost";
const HAS_WINDOW = typeof window !== "undefined";
const withWindow = <T>(fn: (win: Window & typeof globalThis) => T) =>
  HAS_WINDOW ? fn(window as Window & typeof globalThis) : undefined;
const locationMock: Location = {
  ancestorOrigins: {
    contains: vi.fn(() => false),
    item: vi.fn(() => null),
    length: 0,
  } as unknown as DOMStringList,
  assign: vi.fn(),
  hash: "",
  host: "localhost",
  hostname: "localhost",
  href: `${LOCATION_ORIGIN}/`,
  origin: LOCATION_ORIGIN,
  pathname: "/",
  port: "",
  protocol: "http:",
  reload: vi.fn(),
  replace: vi.fn(),
  search: "",
};

withWindow((win) =>
  Object.defineProperty(win, "location", {
    configurable: true,
    value: locationMock,
  })
);

vi.mock("@/components/ui/use-toast", () => ({
  toast: MOCK_TOAST,
  useToast: vi.fn(() => ({
    dismiss: vi.fn(),
    toast: MOCK_TOAST,
    toasts: [],
  })),
}));

// Zustand middleware mocks (used by stores)
vi.mock("zustand/middleware", () => ({
  combine: <T>(fn: T) => fn,
  devtools: <T>(fn: T) => fn,
  persist: <T>(fn: T) => fn,
  subscribeWithSelector: <T>(fn: T) => fn,
}));

// React Query and Supabase mocks migrated to @/test/mocks/react-query.ts and supabase.ts
// Import/use in individual test files: import { mockReactQuery, mockSupabase } from '@/test/mocks/*'; mockReactQuery();
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
    default: (props: Record<string, unknown> & { src?: string; alt?: string; fill?: boolean }) => {
      const { src, alt, fill, ...rest } = props ?? {};
      // Convert fill prop to style for img element (fill makes image fill parent container)
      const style = fill
        ? { position: "absolute", inset: 0, width: "100%", height: "100%" }
        : undefined;
      return React.createElement("img", {
        alt: alt ?? "",
        src: typeof src === "string" ? src : "",
        style,
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
const IS_JSDOM_ENVIRONMENT = HAS_WINDOW;

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

// Suppress React act() warnings during test runs to prevent console flooding and OOM.
// These warnings are being addressed systematically in a separate effort.
// Tests that expect specific console output should use vi.spyOn(console, "error")
// locally and restore it after the test.
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  const firstArg = args[0];
  if (
    typeof firstArg === "string" &&
    (firstArg.includes("not wrapped in act") ||
      firstArg.includes("Warning: An update to"))
  ) {
    return;
  }
  originalConsoleError.call(console, ...args);
};

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

  // Provide sane defaults for client-visible env used in component barrels
  // to avoid validation failures when importing UI modules in tests.
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "http://localhost:54321";
  }
  if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key";
  }
}

beforeEach(() => {
  if (!vi.isFakeTimers()) {
    vi.useFakeTimers();
  }
});

afterEach(() => {
  if (vi.isFakeTimers()) {
    vi.runOnlyPendingTimers();
    vi.clearAllTimers();
    vi.useRealTimers();
  } else {
    vi.useRealTimers();
  }
  cleanup();
  resetTestQueryClient();
  vi.restoreAllMocks();
});
