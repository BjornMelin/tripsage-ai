/**
 * @fileoverview Shared test utilities for tool testing.
 *
 * Provides mocks and helpers for MCP, HTTP, and Redis flows to reduce
 * duplication across tool test suites.
 */

import type { Redis } from "@upstash/redis";
import { vi } from "vitest";

/**
 * Mock Redis instance for tool tests.
 *
 * Provides get/set methods with in-memory storage.
 */
export function createMockRedis(): Redis {
  const store = new Map<string, unknown>();
  return {
    get: vi.fn(async (key: string) => store.get(key) ?? null),
    // biome-ignore lint/suspicious/useAwait: Mock function doesn't need await
    set: vi.fn(async (key: string, value: unknown) => {
      store.set(key, value);
      return "OK";
    }),
  } as unknown as Redis;
}

/**
 * Mock MCP tool execution result.
 *
 * @param data - Result data to return.
 * @returns Mock tool execute function.
 */
export function createMockMcpTool(data: unknown) {
  return {
    execute: vi.fn(async () => data),
  };
}

/**
 * Mock HTTP response for fetch.
 *
 * @param data - JSON data to return.
 * @param ok - Whether response is OK (default: true).
 * @param status - HTTP status code (default: 200).
 * @returns Mock Response object.
 */
export function createMockHttpResponse(
  data: unknown,
  ok = true,
  status = 200
): Response {
  return {
    json: vi.fn(async () => data),
    ok,
    status,
    text: vi.fn(async () => JSON.stringify(data)),
  } as unknown as Response;
}
