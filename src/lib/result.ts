/**
 * @fileoverview Canonical Result type used across server actions and route boundaries.
 */

import type { z } from "zod";

export type ResultOk<T> = { ok: true; data: T };
export type ResultErr<E> = { ok: false; error: E };
export type Result<T, E> = ResultOk<T> | ResultErr<E>;

export function ok<T>(data: T): ResultOk<T> {
  return { data, ok: true };
}

export function err<E>(error: E): ResultErr<E> {
  return { error, ok: false };
}

export type FieldErrors = Record<string, string[]>;

export type ResultError = {
  error: string;
  reason: string;
  issues?: ValidationIssues;
  fieldErrors?: FieldErrors;
};

/**
 * Converts a Zod error into a simple fieldErrors map suitable for forms.
 *
 * - Keys are dot-joined issue paths (e.g. "user.email").
 * - Root issues are stored under "_form".
 */
export function zodErrorToFieldErrors(zodError: z.ZodError): FieldErrors {
  const fieldErrors: FieldErrors = {};

  for (const issue of zodError.issues) {
    const key = issue.path.length > 0 ? issue.path.join(".") : "_form";
    const existing = fieldErrors[key];
    if (existing) {
      existing.push(issue.message);
    } else {
      fieldErrors[key] = [issue.message];
    }
  }

  return fieldErrors;
}

export type ValidationIssues = z.core.$ZodIssue[];
