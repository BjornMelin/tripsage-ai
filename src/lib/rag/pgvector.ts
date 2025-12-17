/**
 * @fileoverview pgvector serialization helpers (number[] -> string literal).
 */

import "server-only";

export function toPgvector(embedding: readonly number[]): string {
  const parts = embedding.map((value, idx) => {
    if (!Number.isFinite(value)) {
      throw new Error(`Invalid embedding value at index ${idx}`);
    }
    // Intentionally preserve JavaScript numeric string formatting (including scientific
    // notation) to avoid rounding/precision changes; pgvector accepts this input form.
    return String(value);
  });
  return `[${parts.join(",")}]`;
}
