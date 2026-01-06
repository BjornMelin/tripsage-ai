/**
 * @fileoverview Boundary validation helpers for server entrypoints (Route Handlers + Server Actions).
 */

import "server-only";

import type { z } from "zod";
import {
  PayloadTooLargeError,
  RequestBodyAlreadyReadError,
  readRequestBodyBytesWithLimit,
} from "@/lib/http/body";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";

function parseWithSchema<Schema extends z.ZodTypeAny>(
  schema: Schema,
  data: unknown,
  options?: { reason?: string }
): Result<z.infer<Schema>, ResultError> {
  const parsed = schema.safeParse(data);
  if (parsed.success) return ok(parsed.data);

  return err({
    error: "invalid_request",
    fieldErrors: zodErrorToFieldErrors(parsed.error),
    issues: parsed.error.issues,
    reason: options?.reason ?? "Request validation failed",
  });
}

type MultiValueScalar = FormDataEntryValue | string;

function withMultiValueRecord<Value extends MultiValueScalar>(
  record: Record<string, Value | Value[]>,
  key: string,
  value: Value
) {
  const existing = record[key];
  if (existing === undefined) {
    record[key] = value;
    return;
  }
  if (Array.isArray(existing)) {
    existing.push(value);
    return;
  }
  record[key] = [existing, value];
}

/**
 * Parse and validate a JSON request body with a hard size limit.
 *
 * Never call `request.json()` directly in Route Handlers; use this helper to ensure
 * schema validation and bounded reads.
 */
export async function parseJson<Schema extends z.ZodTypeAny>(
  req: Request,
  schema: Schema,
  options: { maxBytes?: number; reason?: string } = {}
): Promise<Result<z.infer<Schema>, ResultError>> {
  const maxBytes = options.maxBytes ?? 64 * 1024;

  let rawBody: string;
  try {
    const bytes = await readRequestBodyBytesWithLimit(req, maxBytes);
    rawBody = new TextDecoder().decode(bytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return err({
        error: "payload_too_large",
        reason: "Request body exceeds limit",
      });
    }
    if (error instanceof RequestBodyAlreadyReadError) {
      return err({
        error: "invalid_request",
        reason: "Request body has already been read",
      });
    }
    return err({
      error: "invalid_request",
      reason: "Failed to read request body",
    });
  }

  let json: unknown;
  try {
    json = JSON.parse(rawBody) as unknown;
  } catch {
    return err({
      error: "invalid_request",
      reason: "Malformed JSON in request body",
    });
  }

  return parseWithSchema(schema, json, options);
}

type FormDataEntry = FormDataEntryValue;
type FormDataRecord = Record<string, FormDataEntry | FormDataEntry[]>;

function formDataToRecord(formData: FormData): FormDataRecord {
  const record: FormDataRecord = {};
  for (const [key, value] of formData.entries()) {
    withMultiValueRecord(record, key, value);
  }
  return record;
}

/**
 * Parse and validate a FormData payload against a Zod schema.
 *
 * This helper does not read the request body; it converts an existing `FormData`
 * object into a plain record for schema validation.
 */
export function parseFormData<Schema extends z.ZodTypeAny>(
  formData: FormData,
  schema: Schema,
  options?: { reason?: string }
): Result<z.infer<Schema>, ResultError> {
  return parseWithSchema(schema, formDataToRecord(formData), options);
}

type SearchParamsRecord = Record<string, string | string[]>;

function searchParamsToRecord(searchParams: URLSearchParams): SearchParamsRecord {
  const record: SearchParamsRecord = {};
  for (const [key, value] of searchParams.entries()) {
    withMultiValueRecord(record, key, value);
  }
  return record;
}

/**
 * Parse and validate URL search params against a Zod schema.
 *
 * The schema should use `z.coerce.*` when coercion is desired (all raw values are
 * strings or string arrays).
 */
export function parseSearchParams<Schema extends z.ZodTypeAny>(
  urlOrSearchParams: URL | URLSearchParams,
  schema: Schema,
  options?: { reason?: string }
): Result<z.infer<Schema>, ResultError> {
  const searchParams =
    urlOrSearchParams instanceof URL
      ? urlOrSearchParams.searchParams
      : urlOrSearchParams;

  return parseWithSchema(schema, searchParamsToRecord(searchParams), options);
}

/**
 * Parse and validate route params against a Zod schema.
 */
export function parseParams<Schema extends z.ZodTypeAny>(
  params: Record<string, string | string[] | undefined>,
  schema: Schema,
  options?: { reason?: string }
): Result<z.infer<Schema>, ResultError> {
  return parseWithSchema(schema, params, options);
}
