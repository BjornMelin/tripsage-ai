/**
 * @fileoverview HTTP request utilities for Expedia Rapid API.
 *
 * Handles core HTTP communication with Expedia's Rapid API including telemetry
 * instrumentation, error handling, and response validation.
 */

import { SpanStatusCode } from "@opentelemetry/api";
import type { z } from "zod";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import type { ExpediaRequestContext } from "./client-types";
import { ExpediaApiError } from "./client-types";

/**
 * Performs HTTP request to Expedia Rapid API with telemetry and error handling.
 *
 * @template T - Response type, validated against provided schema.
 * @param params - Request configuration including URL, headers, body, and schema.
 * @returns Promise resolving to validated response data.
 * @throws {ExpediaApiError} For API errors with structured error information.
 */
export function performRapidRequest<T>({
  baseUrl,
  path,
  init,
  context,
  schema,
  spanName,
  buildHeaders,
}: {
  baseUrl: string;
  path: string;
  init?: RequestInit;
  context?: ExpediaRequestContext;
  schema?: z.ZodSchema<T>;
  spanName?: string;
  buildHeaders: (
    existing: HeadersInit | undefined,
    ctx?: ExpediaRequestContext
  ) => Headers;
}): Promise<T> {
  const url = `${baseUrl}${path}`;
  const method = init?.method ?? "GET";

  return withTelemetrySpan(
    spanName ?? "rapid.request",
    {
      attributes: {
        "rapid.base_url": baseUrl,
        "rapid.endpoint": path,
        "rapid.method": method,
      },
      redactKeys: ["rapid.base_url"],
    },
    async (span) => {
      const response = await fetch(url, {
        ...init,
        headers: buildHeaders(init?.headers, context),
      });

      span.setAttribute("rapid.status_code", response.status);

      if (!response.ok) {
        const errorBody = await response
          .json()
          .catch(async () => ({ message: await response.text().catch(() => "") }));
        const message =
          typeof errorBody?.message === "string"
            ? errorBody.message
            : response.statusText;
        const code =
          typeof errorBody?.code === "string" ? errorBody.code : "EPS_API_ERROR";

        span.setAttribute("rapid.error_code", code);
        span.setAttribute("rapid.error_message", message);
        span.setStatus({ code: SpanStatusCode.ERROR });

        throw new ExpediaApiError(message, code, response.status, { path });
      }

      const body = (await response.json()) as T;
      const validated = schema ? schema.parse(body) : body;
      span.setStatus({ code: SpanStatusCode.OK });
      return validated;
    }
  );
}
