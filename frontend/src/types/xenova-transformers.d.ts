/**
 * @fileoverview Type declarations for optional @xenova/transformers dependency.
 *
 * This module may not be installed, so we provide minimal type declarations
 * to allow TypeScript compilation without the package being present.
 */

declare module "@xenova/transformers" {
  export function pipeline(
    task: string,
    model: string,
    options?: Record<string, unknown>
  ): Promise<
    (
      input: string,
      options?: Record<string, unknown>
    ) => Promise<{
      data: Float32Array | Float64Array | Int32Array;
    }>
  >;
}
