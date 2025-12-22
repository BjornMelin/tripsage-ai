/**
 * @fileoverview Deep equality for JSON-like values with guardrails.
 */

import { isPlainObject } from "@/lib/utils/type-guards";

export const DIRTY_CHECK_MAX_DEPTH = 20;
export const SLOW_DIRTY_CHECK_MS = 2;

export const DIRTY_CHECK_PRIORITY_KEYS = [
  "origin",
  "destination",
  "departureDate",
  "returnDate",
  "checkIn",
  "checkOut",
  "date",
  "query",
] as const;

export interface DeepEqualLogger {
  warn: (message: string, meta?: Record<string, unknown>) => void;
}

export interface DeepEqualJsonLikeOptions {
  logger?: DeepEqualLogger;
  maxDepth?: number;
  nowMs?: () => number;
  priorityKeys?: readonly string[];
  slowThresholdMs?: number;
}

const defaultNowMs = (): number =>
  typeof performance !== "undefined" ? performance.now() : Date.now();

const sizeOf = (value: unknown): number => {
  if (Array.isArray(value)) return value.length;
  if (isPlainObject(value)) return Object.keys(value).length;
  return 0;
};

const deepEqualJsonLikeInner = (
  a: unknown,
  b: unknown,
  depth: number,
  maxDepth: number,
  priorityKeys: readonly string[],
  priorityKeySet: ReadonlySet<string>,
  context: {
    hitMaxDepth: boolean;
    maxDepthHitDepth: number | null;
    objectKeySetsByDepth: Array<Set<string> | undefined>;
  }
): boolean => {
  if (depth > maxDepth) {
    context.hitMaxDepth = true;
    context.maxDepthHitDepth = depth;
    return false;
  }

  if (Object.is(a, b)) return true;

  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i += 1) {
      if (
        !deepEqualJsonLikeInner(
          a[i],
          b[i],
          depth + 1,
          maxDepth,
          priorityKeys,
          priorityKeySet,
          context
        )
      ) {
        return false;
      }
    }
    return true;
  }

  if (!isPlainObject(a) || !isPlainObject(b)) return false;

  // Short-circuit on known high-churn keys first.
  for (const key of priorityKeys) {
    const aValue = a[key];
    const bValue = b[key];
    if (aValue === undefined && bValue === undefined) continue;
    if (
      !deepEqualJsonLikeInner(
        aValue,
        bValue,
        depth + 1,
        maxDepth,
        priorityKeys,
        priorityKeySet,
        context
      )
    ) {
      return false;
    }
  }

  const aKeys = Object.keys(a)
    .filter((key) => a[key] !== undefined)
    .filter((key) => !priorityKeySet.has(key));
  const bKeys = Object.keys(b)
    .filter((key) => b[key] !== undefined)
    .filter((key) => !priorityKeySet.has(key));
  if (aKeys.length !== bKeys.length) return false;

  const existingKeySet = context.objectKeySetsByDepth[depth];
  const bKeySet = existingKeySet ?? new Set<string>();
  if (existingKeySet) {
    bKeySet.clear();
  } else {
    context.objectKeySetsByDepth[depth] = bKeySet;
  }

  for (const key of bKeys) {
    bKeySet.add(key);
  }
  for (const key of aKeys) {
    if (!bKeySet.has(key)) return false;
    if (
      !deepEqualJsonLikeInner(
        a[key],
        b[key],
        depth + 1,
        maxDepth,
        priorityKeys,
        priorityKeySet,
        context
      )
    ) {
      return false;
    }
  }
  return true;
};

/**
 * Deep equality check for JSON-like values.
 *
 * - Treats `undefined` object properties as absent.
 * - Enforces a max depth to guard against cyclic/degenerate inputs.
 * - Optionally logs warnings for max-depth hits and slow comparisons.
 */
export const deepEqualJsonLike = (
  a: unknown,
  b: unknown,
  options: DeepEqualJsonLikeOptions = {}
): boolean => {
  const maxDepth = options.maxDepth ?? DIRTY_CHECK_MAX_DEPTH;
  const slowThresholdMs = options.slowThresholdMs ?? SLOW_DIRTY_CHECK_MS;
  const priorityKeys = options.priorityKeys ?? DIRTY_CHECK_PRIORITY_KEYS;
  const priorityKeySet = new Set(priorityKeys);
  const nowMs = options.nowMs ?? defaultNowMs;
  const logger = options.logger;

  const context = {
    hitMaxDepth: false,
    maxDepthHitDepth: null,
    objectKeySetsByDepth: [],
  };
  const start = nowMs();
  const result = deepEqualJsonLikeInner(
    a,
    b,
    0,
    maxDepth,
    priorityKeys,
    priorityKeySet,
    context
  );

  if (context.hitMaxDepth) {
    logger?.warn("deepEqualJsonLike maxDepth exceeded", {
      maxDepth,
      ...(context.maxDepthHitDepth !== null ? { depth: context.maxDepthHitDepth } : {}),
    });
  }

  const durationMs = nowMs() - start;
  if (durationMs > slowThresholdMs) {
    logger?.warn("Slow dirty-check comparison", {
      aSize: sizeOf(a),
      bSize: sizeOf(b),
      durationMs: Math.round(durationMs * 1000) / 1000,
      maxDepth,
      result,
    });
  }

  return result;
};
