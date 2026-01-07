/**
 * @fileoverview Shared helpers for trip server action implementations.
 */

import "server-only";

import { createServerLogger } from "@/lib/telemetry/logger";

export const logger = createServerLogger("trips.actions");

export function normalizeIsoDate(value: string): string {
  const trimmed = value.trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(trimmed)) {
    return trimmed.slice(0, 10);
  }

  return trimmed;
}

export function normalizeTripDateFilter(value: string | undefined): string | undefined {
  if (!value) return undefined;
  return normalizeIsoDate(value);
}

export function isPermissionDeniedError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const maybe = error as { code?: unknown; details?: unknown; message?: unknown };

  const code = typeof maybe.code === "string" ? maybe.code : null;
  if (code === "42501") return true;

  const details = typeof maybe.details === "string" ? maybe.details : "";
  const message = typeof maybe.message === "string" ? maybe.message : "";
  const combined = `${message} ${details}`.toLowerCase();
  return (
    combined.includes("permission denied") ||
    combined.includes("row-level security") ||
    combined.includes("violates row-level security")
  );
}

export function isForeignKeyViolationError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  return (error as { code?: unknown }).code === "23503";
}

export function normalizePlaceIdForStorage(placeId: string): string {
  return placeId.startsWith("places/") ? placeId.slice("places/".length) : placeId;
}
