/**
 * @fileoverview Shared QueryClient helpers for tests.
 *
 * Keep this module React-free so it can be used from setup files without
 * pulling in component providers.
 */

import type { QueryClient } from "@tanstack/react-query";
import { createMockQueryClient } from "./query";

let sharedQueryClient: QueryClient | null = null;

export const getTestQueryClient = (): QueryClient => {
  if (!sharedQueryClient) {
    sharedQueryClient = createMockQueryClient();
  }
  return sharedQueryClient;
};

export const resetTestQueryClient = (): void => {
  if (!sharedQueryClient) return;
  sharedQueryClient.getQueryCache().clear();
  sharedQueryClient.getMutationCache().clear();
};
