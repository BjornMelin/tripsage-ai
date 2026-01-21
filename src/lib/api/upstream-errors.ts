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
