/**
 * @fileoverview Minimal stub of @xenova/transformers for Vitest.
 *
 * The real package is large and not installed in the test environment.
 * Tool code never executes this stub because generateEmbedding is mocked,
 * but the module must exist so Vite can resolve dynamic imports.
 */

export const env = {
  allowLocalModels: () => undefined,
  cacheDir: ".cache",
  localModelPath: ".models",
};

export function pipeline() {
  return async () => ({
    data: [[0.01, 0.02, 0.03]],
  });
}
