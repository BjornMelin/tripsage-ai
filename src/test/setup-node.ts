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
