/**
 * @fileoverview Shared helpers for AI SDK timeout configuration.
 */

import type { TimeoutConfiguration } from "ai";

const MIN_TIMEOUT_MS = 5_000;
const DEFAULT_STEP_TIMEOUT_MS = parseTimeoutEnv("AI_DEFAULT_STEP_TIMEOUT_MS", 20_000);

/** Default total timeout for AI SDK calls (milliseconds). */
export const DEFAULT_AI_TIMEOUT_MS = parseTimeoutEnv("AI_DEFAULT_TIMEOUT_MS", 30_000);

function parseTimeoutEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  const parsed = raw ? Number(raw) : Number.NaN;
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return Math.max(MIN_TIMEOUT_MS, fallback);
  }
  return Math.max(MIN_TIMEOUT_MS, Math.round(parsed));
}

function normalizeTimeoutMs(value: number): number {
  if (!Number.isFinite(value) || value <= 0) {
    return MIN_TIMEOUT_MS;
  }
  return Math.max(MIN_TIMEOUT_MS, Math.round(value));
}

/**
 * Builds a TimeoutConfiguration from total and optional step durations.
 *
 * @param totalMs - Total timeout in milliseconds.
 * @param stepMs - Optional per-step timeout in milliseconds.
 * @returns Timeout configuration or undefined when totalMs is invalid.
 */
export function buildTimeoutConfig(
  totalMs?: number,
  stepMs?: number
): TimeoutConfiguration | undefined {
  if (typeof totalMs !== "number" || !Number.isFinite(totalMs) || totalMs <= 0) {
    return undefined;
  }

  const normalizedTotal = normalizeTimeoutMs(totalMs);
  const desiredStep =
    typeof stepMs === "number" && Number.isFinite(stepMs) && stepMs > 0
      ? stepMs
      : DEFAULT_STEP_TIMEOUT_MS;
  const normalizedStep = Math.min(normalizedTotal, normalizeTimeoutMs(desiredStep));

  return { stepMs: normalizedStep, totalMs: normalizedTotal };
}

/**
 * Builds a TimeoutConfiguration from seconds-based inputs.
 *
 * @param timeoutSeconds - Total timeout in seconds.
 * @param stepMs - Optional per-step timeout in milliseconds.
 * @returns Timeout configuration or undefined when timeoutSeconds is invalid.
 */
export function buildTimeoutConfigFromSeconds(
  timeoutSeconds?: number,
  stepMs?: number
): TimeoutConfiguration | undefined {
  if (
    typeof timeoutSeconds !== "number" ||
    !Number.isFinite(timeoutSeconds) ||
    timeoutSeconds <= 0
  ) {
    return undefined;
  }

  return buildTimeoutConfig(timeoutSeconds * 1000, stepMs);
}
