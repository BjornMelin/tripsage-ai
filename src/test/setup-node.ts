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
import { afterAll, afterEach, beforeAll, beforeEach, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { MSW_SUPABASE_URL } from "./msw/constants";
import { server } from "./msw/server";

// Default to failing tests on unexpected network calls. For local debugging only,
// you can relax this with `MSW_ON_UNHANDLED_REQUEST=warn` or `bypass`.
const onUnhandledRequest =
  (process.env.MSW_ON_UNHANDLED_REQUEST as "bypass" | "error" | "warn" | undefined) ??
  "error";
const DEBUG_OPEN_HANDLES = process.env.VITEST_DEBUG_OPEN_HANDLES === "1";

// Provide sane defaults for client-visible env used in some client components.
if (typeof process !== "undefined" && process.env) {
  const env = process.env as Record<string, string | undefined>;
  env.NODE_ENV ||= "test";
  env.NEXT_PUBLIC_SUPABASE_URL ||= MSW_SUPABASE_URL;
  env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||= "test-anon-key";
  // SECURITY: Simulate Vercel environment in tests so proxy headers (X-Forwarded-For,
  // X-Real-IP) are trusted. In production, Vercel sets this automatically.
  // Tests that need to verify untrusted proxy behavior should explicitly unset this.
  env.VERCEL ||= "1";
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

beforeEach(async () => {
  // Provide a default rate limit factory that always succeeds.
  // Tests that need to override this can call setRateLimitFactoryForTests themselves.
  // Use dynamic import and guard with try/catch since some tests mock this module.
  try {
    const factoryModule = await import("@/lib/api/factory");
    if (typeof factoryModule.setRateLimitFactoryForTests === "function") {
      factoryModule.setRateLimitFactoryForTests(async () => ({
        limit: 100,
        remaining: 99,
        reset: Date.now() + 60_000,
        success: true,
      }));
    }
  } catch {
    // Module mocked or unavailable - tests handle their own rate limiting
  }
});

afterAll(() => {
  server.close();

  if (!DEBUG_OPEN_HANDLES) return;
  const globalFlag = globalThis as Record<string, unknown>;
  if (globalFlag.__TRIPSAGE_VITEST_OPEN_HANDLES_DUMPED__) return;
  globalFlag.__TRIPSAGE_VITEST_OPEN_HANDLES_DUMPED__ = true;

  const timeout = setTimeout(() => {
    console.log("[vitest-debug] dumping active handles/requests…");
    const processWithDebugMethods = process as typeof process & {
      _getActiveHandles?: () => unknown[];
      _getActiveRequests?: () => unknown[];
    };
    const activeHandles = processWithDebugMethods._getActiveHandles?.();
    const activeRequests = processWithDebugMethods._getActiveRequests?.();

    const summarize = (items: unknown[] | undefined) => {
      const counts = new Map<string, number>();
      for (const item of items ?? []) {
        const name =
          typeof item === "object" && item && "constructor" in item
            ? String(
                (() => {
                  const ctorName = unsafeCast<{ constructor?: { name?: unknown } }>(
                    item
                  ).constructor?.name;
                  return typeof ctorName === "string" ? ctorName : "Object";
                })()
              )
            : typeof item;
        counts.set(name, (counts.get(name) ?? 0) + 1);
      }
      return [...counts.entries()].sort((a, b) => b[1] - a[1]);
    };

    console.log("[vitest-debug] active handles:", summarize(activeHandles));
    console.log("[vitest-debug] active requests:", summarize(activeRequests));
  }, 1000);

  timeout.unref();
});

afterEach(async () => {
  server.resetHandlers();

  // Reset rate limit factory to avoid cross-test pollution.
  // Note: beforeEach will set it again before the next test.
  try {
    const factoryModule = await import("@/lib/api/factory");
    if (typeof factoryModule.setRateLimitFactoryForTests === "function") {
      factoryModule.setRateLimitFactoryForTests(null);
    }
  } catch {
    // Module mocked or unavailable
  }

  // Only restore timers if they were explicitly enabled in the test.
  // Tests that need fake timers should use withFakeTimers() utility.
  if (vi.isFakeTimers()) {
    vi.runOnlyPendingTimers();
    vi.clearAllTimers();
    vi.useRealTimers();
  }
});
