/**
 * @fileoverview Helpers for formatting upstream error responses.
 */

export type UpstreamErrorOptions = {
  status: number;
  service: string;
  details?: string | null;
  maxDetailLength?: number;
};

const DEFAULT_MAX_DETAIL_LENGTH = 200;

/**
 * Builds a standardized upstream error reason string.
 *
 * For all statuses the base message is "`<service> error: <status>`". For client errors
 * (status in the 400–499 range) and when `details` contains non-blank text, the message
 * appends "Details: <text>" where `<text>` is `details` trimmed and truncated to
 * `maxDetailLength` (defaults to 200). For statuses >= 500 or < 400, or when `details`
 * is missing/blank, the base message is returned.
 *
 * @param options - Formatting options including `service`, `status`, optional `details`,
 *   and optional `maxDetailLength` (defaults to 200)
 * @returns The formatted error reason string
 */
export function formatUpstreamErrorReason(options: UpstreamErrorOptions): string {
  const { service, status, details } = options;
  const maxDetailLength = options.maxDetailLength ?? DEFAULT_MAX_DETAIL_LENGTH;
  const base = `${service} error: ${status}`;

  if (status >= 500 || status < 400) {
    return base;
  }

  const trimmed = details?.trim();
  if (!trimmed) return base;

  const truncated =
    trimmed.length > maxDetailLength ? trimmed.slice(0, maxDetailLength) : trimmed;

  return `${base}. Details: ${truncated}`;
}
