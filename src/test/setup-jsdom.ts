/**
 * @fileoverview Vitest setup for JSDOM test projects (React/UI).
 *
 * This file layers on top of `src/test/setup-node.ts` and adds DOM mocks,
 * Next.js shims, and React Testing Library cleanup.
 */

import "./setup-node";

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import React from "react";
import { afterAll, afterEach, vi } from "vitest";
import { resetTestQueryClient } from "./helpers/query-client";

(globalThis as unknown as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT ??= true;

// Minimal toast mock (used by many components)
type UnknownRecord = Record<string, unknown>;
const MOCK_TOAST = vi.fn((_props?: UnknownRecord) => ({
  dismiss: vi.fn(),
  id: "toast-1",
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

// Zustand middleware mocks (used by stores)
vi.mock("zustand/middleware", () => ({
  combine: <T>(fn: T) => fn,
  devtools: <T>(fn: T) => fn,
  persist: <T>(fn: T) => fn,
  subscribeWithSelector: <T>(fn: T) => fn,
}));

// React Query helpers live in @/test/helpers/query; Supabase helpers in @/test/mocks/supabase.
// Import per test as needed instead of global mocks.
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
    default: (
      props: Record<string, unknown> & { src?: string; alt?: string; fill?: boolean }
    ) => {
      const { src, alt, fill, ...rest } = props ?? {};
      const style = fill
        ? { height: "100%", inset: 0, position: "absolute", width: "100%" }
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

if (typeof window !== "undefined") {
  class MockResizeObserver implements ResizeObserver {
    observe(): void {
      /* noop */
    }
    unobserve(): void {
      /* noop */
    }
    disconnect(): void {
      /* noop */
    }
  }

  class MockIntersectionObserver implements IntersectionObserver {
    readonly root: Element | Document | null = null;
    readonly rootMargin = "";
    readonly thresholds: number[] = [];

    observe(): void {
      /* noop */
    }
    unobserve(): void {
      /* noop */
    }
    disconnect(): void {
      /* noop */
    }
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  }

  const WINDOW_REF = globalThis.window as Window & typeof globalThis;

  Object.defineProperty(WINDOW_REF, "matchMedia", {
    configurable: true,
    value: CREATE_MATCH_MEDIA_MOCK(false),
    writable: true,
  });

  Object.defineProperty(WINDOW_REF, "localStorage", {
    configurable: true,
    value: CREATE_MOCK_STORAGE(),
  });

  Object.defineProperty(WINDOW_REF, "sessionStorage", {
    configurable: true,
    value: CREATE_MOCK_STORAGE(),
  });

  Object.defineProperty(globalThis, "ResizeObserver", {
    configurable: true,
    value: MockResizeObserver,
    writable: true,
  });

  Object.defineProperty(globalThis, "IntersectionObserver", {
    configurable: true,
    value: MockIntersectionObserver,
    writable: true,
  });

  Object.defineProperty(globalThis, "CSS", {
    configurable: true,
    value: { supports: vi.fn().mockReturnValue(false) },
    writable: true,
  });
}

// Suppress React act() warnings during test runs to prevent console flooding.
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  const firstArg = args[0];
  if (
    typeof firstArg === "string" &&
    (firstArg.includes("not wrapped in act") ||
      firstArg.includes("Warning: An update to") ||
      firstArg.includes("Not implemented: navigation"))
  ) {
    return;
  }
  originalConsoleError.call(console, ...args);
};

afterAll(() => {
  console.error = originalConsoleError;
});

afterEach(() => {
  if (typeof document !== "undefined") {
    cleanup();
  }
  resetTestQueryClient();
});
