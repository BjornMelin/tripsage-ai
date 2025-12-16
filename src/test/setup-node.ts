/**
 * @fileoverview Vitest setup for Node.js test projects.
 *
 * Keep this file lightweight: it runs before every test file. Prefer per-test
 * helpers for feature-specific mocks. DOM/React-specific setup lives in
 * `src/test/setup-jsdom.ts`.
 */

import "./setup";

import {
  ReadableStream as NodeReadableStream,
  TransformStream as NodeTransformStream,
  WritableStream as NodeWritableStream,
} from "node:stream/web";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { server } from "./msw/server";

const onUnhandledRequest = process.env.CI ? "error" : "warn";
const DEBUG_OPEN_HANDLES = process.env.VITEST_DEBUG_OPEN_HANDLES === "1";

// Provide sane defaults for client-visible env used in some client components.
if (typeof process !== "undefined" && process.env) {
  const env = process.env as Record<string, string | undefined>;
  env.NODE_ENV ||= "test";
  env.NEXT_PUBLIC_SUPABASE_URL ||= "http://localhost:54321";
  env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||= "test-anon-key";
}

// Provide Web Streams polyfills for environments missing them (used by
// eventsource-parser / AI SDK transport in tests).
const globalAny = globalThis as Record<string, unknown>;
if (!globalAny.ReadableStream) {
  Object.defineProperty(globalThis, "ReadableStream", {
    configurable: true,
    value: NodeReadableStream,
    writable: true,
  });
}
if (!globalAny.WritableStream) {
  Object.defineProperty(globalThis, "WritableStream", {
    configurable: true,
    value: NodeWritableStream,
    writable: true,
  });
}
if (!globalAny.TransformStream) {
  Object.defineProperty(globalThis, "TransformStream", {
    configurable: true,
    value: NodeTransformStream,
    writable: true,
  });
}

beforeAll(() => {
  // Start MSW server to intercept HTTP requests.
  server.listen({ onUnhandledRequest });
});

afterAll(() => {
  server.close();

  if (!DEBUG_OPEN_HANDLES) return;
  const globalFlag = globalThis as unknown as Record<string, unknown>;
  if (globalFlag.__TRIPSAGE_VITEST_OPEN_HANDLES_DUMPED__) return;
  globalFlag.__TRIPSAGE_VITEST_OPEN_HANDLES_DUMPED__ = true;

  const timeout = setTimeout(() => {
    // biome-ignore lint/suspicious/noConsoleLog: debug output enabled via env var
    console.log("[vitest-debug] dumping active handles/requests…");
    const activeHandles = (
      process as unknown as {
        _getActiveHandles?: () => unknown[];
        _getActiveRequests?: () => unknown[];
      }
    )._getActiveHandles?.();
    const activeRequests = (
      process as unknown as {
        _getActiveRequests?: () => unknown[];
      }
    )._getActiveRequests?.();

    const summarize = (items: unknown[] | undefined) => {
      const counts = new Map<string, number>();
      for (const item of items ?? []) {
        const name =
          typeof item === "object" && item && "constructor" in item
            ? // biome-ignore lint/suspicious/noExplicitAny: debug-only safe cast
              String((item as any).constructor?.name ?? "Object")
            : typeof item;
        counts.set(name, (counts.get(name) ?? 0) + 1);
      }
      return [...counts.entries()].sort((a, b) => b[1] - a[1]);
    };

    // biome-ignore lint/suspicious/noConsoleLog: debug output enabled via env var
    console.log("[vitest-debug] active handles:", summarize(activeHandles));
    // biome-ignore lint/suspicious/noConsoleLog: debug output enabled via env var
    console.log("[vitest-debug] active requests:", summarize(activeRequests));
  }, 1000);

  timeout.unref();
});

afterEach(() => {
  server.resetHandlers();

  // Only restore timers if they were explicitly enabled in the test.
  // Tests that need fake timers should use withFakeTimers() utility.
  if (vi.isFakeTimers()) {
    vi.runOnlyPendingTimers();
    vi.clearAllTimers();
    vi.useRealTimers();
  }
});
