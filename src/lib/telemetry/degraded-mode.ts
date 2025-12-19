/**
 * @fileoverview Deduped operational alerts for degraded infrastructure fallbacks.
 */

import "server-only";

import type { OperationalAlertOptions } from "@/lib/telemetry/alerts";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";

const lastEmittedAtByKey = new Map<string, number>();
const MAX_DEDUPE_ENTRY_AGE_MS = 24 * 60 * 60 * 1000; // 24h
const CLEANUP_INTERVAL_MS = 10 * 60 * 1000; // 10m
const CLEANUP_SIZE_THRESHOLD = 1000;
let lastCleanupAt = 0;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (typeof value !== "object" || value === null) return false;
  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

function normalizeForStableJson(value: unknown): unknown {
  if (value === null) return null;
  if (value === undefined) return null;
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  if (typeof value === "bigint") {
    return value.toString();
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeForStableJson(entry));
  }
  if (isPlainObject(value)) {
    const keys = Object.keys(value).sort();
    const normalized: Record<string, unknown> = {};
    for (const key of keys) {
      normalized[key] = normalizeForStableJson(value[key]);
    }
    return normalized;
  }
  return String(value);
}

function stableStringifyAttributes(attributes: Record<string, unknown>): string {
  return JSON.stringify(normalizeForStableJson(attributes));
}

function maybeCleanup(now: number): void {
  const shouldCleanup =
    now - lastCleanupAt > CLEANUP_INTERVAL_MS ||
    lastEmittedAtByKey.size > CLEANUP_SIZE_THRESHOLD;
  if (!shouldCleanup) return;

  lastCleanupAt = now;
  for (const [key, timestamp] of Array.from(lastEmittedAtByKey.entries())) {
    if (now - timestamp > MAX_DEDUPE_ENTRY_AGE_MS) {
      lastEmittedAtByKey.delete(key);
    }
  }
}

export function emitOperationalAlertOncePerWindow(
  params: {
    event: string;
    windowMs: number;
  } & OperationalAlertOptions
): void {
  const { event, windowMs, ...options } = params;

  const now = Date.now();
  maybeCleanup(now);
  const dedupeKey = `${event}:${stableStringifyAttributes(options.attributes ?? {})}`;
  const last = lastEmittedAtByKey.get(dedupeKey);
  if (last != null && now - last < windowMs) return;

  lastEmittedAtByKey.set(dedupeKey, now);
  emitOperationalAlert(event, options);
}

export function resetDegradedModeAlertStateForTests(): void {
  lastEmittedAtByKey.clear();
  lastCleanupAt = 0;
}
