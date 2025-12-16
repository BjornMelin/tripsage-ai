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

// Provide sane defaults for client-visible env used in some client components.
if (typeof process !== "undefined" && process.env) {
  process.env.NODE_ENV ||= "test";
  process.env.NEXT_PUBLIC_SUPABASE_URL ||= "http://localhost:54321";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||= "test-anon-key";
}

// Provide Web Streams polyfills for environments missing them (used by
// eventsource-parser / AI SDK transport in tests).
type Rs = typeof ReadableStream;
type Ws = typeof WritableStream;
type Ts = typeof TransformStream;
const GLOBAL_STREAMS = globalThis as typeof globalThis & {
  ReadableStream?: Rs;
  WritableStream?: Ws;
  TransformStream?: Ts;
};
if (!GLOBAL_STREAMS.ReadableStream) {
  (GLOBAL_STREAMS as { ReadableStream?: Rs }).ReadableStream =
    NodeReadableStream as unknown as Rs;
}
if (!GLOBAL_STREAMS.WritableStream) {
  (GLOBAL_STREAMS as { WritableStream?: Ws }).WritableStream =
    NodeWritableStream as unknown as Ws;
}
if (!GLOBAL_STREAMS.TransformStream) {
  (GLOBAL_STREAMS as { TransformStream?: Ts }).TransformStream =
    NodeTransformStream as unknown as Ts;
}

beforeAll(() => {
  // Start MSW server to intercept HTTP requests.
  // Keep "warn" until the suite is fully standardized on explicit handlers.
  server.listen({ onUnhandledRequest: "warn" });
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
