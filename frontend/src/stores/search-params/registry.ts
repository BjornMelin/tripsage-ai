/**
 * @fileoverview Registry for search params handlers.
 *
 * Provides handler registration and lookup for the strategy pattern.
 * Consumers must import handler files separately to trigger registration.
 */

import type { SearchType } from "@schemas/stores";
import type { SearchParamsHandler } from "./types";

const handlers = new Map<SearchType, SearchParamsHandler>();

/**
 * Register a handler for a search type.
 * Called at module load time by each handler.
 *
 * @param handler - The handler to register
 * @throws Error if a handler is already registered for the search type
 */
export function registerHandler<T>(handler: SearchParamsHandler<T>): void {
  if (handlers.has(handler.searchType)) {
    throw new Error(
      `Handler already registered for search type: ${handler.searchType}`
    );
  }
  handlers.set(handler.searchType, handler as SearchParamsHandler);
}

/**
 * Get handler for a search type.
 *
 * @param searchType - The search type to get handler for
 * @returns The handler for the search type
 * @throws Error if no handler is registered for the search type
 */
export function getHandler<T = unknown>(
  searchType: SearchType
): SearchParamsHandler<T> {
  const handler = handlers.get(searchType);
  if (!handler) {
    throw new Error(`No handler registered for search type: ${searchType}`);
  }
  return handler as SearchParamsHandler<T>;
}

/**
 * Check if a handler is registered for a search type.
 *
 * @param searchType - The search type to check
 * @returns True if a handler is registered
 */
export function hasHandler(searchType: SearchType): boolean {
  return handlers.has(searchType);
}

/**
 * Get all registered search types.
 *
 * @returns Array of registered search types
 */
export function getRegisteredTypes(): SearchType[] {
  return Array.from(handlers.keys());
}
