/**
 * @fileoverview Runtime timestamp helpers for pure domain schemas.
 */

type SchemaTimestampReference = Date | number | string;

const getTimestampDate = (reference?: SchemaTimestampReference): Date => {
  const date =
    reference instanceof Date
      ? new Date(reference.getTime())
      : new Date(reference ?? Date.now());

  if (!Number.isFinite(date.getTime())) {
    throw new Error("Invalid schema timestamp reference");
  }

  return date;
};

/**
 * Returns the current runtime timestamp as an ISO 8601 string for schema fallbacks.
 *
 * @param reference - Optional timestamp reference for deterministic tests/callers.
 * @returns ISO timestamp string.
 */
export const schemaNowIso = (reference?: SchemaTimestampReference): string =>
  getTimestampDate(reference).toISOString();
