/**
 * @fileoverview Cross-cutting helpers for API-focused tests (routes + hooks + stores).
 *
 * Exposes QueryClient factories and Zustand store reset utilities so suites can
 * exercise real implementations with deterministic state.
 */

import type { QueryClientConfig } from "@tanstack/react-query";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import type { StoreApi } from "zustand";

/**
 * Create a QueryClient configured for deterministic Vitest runs.
 *
 * @param config Optional overrides for the client default options.
 * @returns QueryClient instance with retries disabled by default.
 */
export function createApiTestQueryClient(config?: QueryClientConfig): QueryClient {
  const { defaultOptions, ...restConfig } = config ?? {};
  return new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { gcTime: 0, retry: false, staleTime: 0 },
      ...defaultOptions,
    },
    ...restConfig,
  });
}

/**
 * Wraps children with a QueryClientProvider using a deterministic client.
 *
 * @param client Optional QueryClient. When omitted a new instance is created.
 * @returns React provider component for use in render/renderHook wrappers.
 */
export function createApiTestWrapper(client = createApiTestQueryClient()) {
  return function ApiTestProviders({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children);
  };
}

type ResettableStore<T> = Pick<StoreApi<T>, "getState" | "setState">;

/**
 * Reset a Zustand store to either its built-in `reset` method (if provided)
 * or to an explicit snapshot.
 *
 * @param store Zustand store hook (from `create`) exposing `getState`/`setState`.
 * @param snapshot Optional partial snapshot or function returning one.
 */
export function resetStoreState<T extends { reset?: () => void }>(
  store: ResettableStore<T>,
  snapshot?: Partial<T> | (() => Partial<T>)
): void {
  act(() => {
    const state = store.getState();
    if (!snapshot && typeof state.reset === "function") {
      state.reset();
      return;
    }

    const nextSnapshot =
      typeof snapshot === "function" ? snapshot() : (snapshot ?? ({} as Partial<T>));

    store.setState(nextSnapshot as T, true);
  });
}
