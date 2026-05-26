/**
 * @fileoverview Agent configuration version identifier helpers.
 */

import { nowIso, secureId } from "@/lib/security/random";

const VERSION_ID_RANDOM_LENGTH = 8;

/**
 * Creates a sortable agent configuration version identifier.
 *
 * Keeps the existing `v<epoch_seconds>_<token>` shape while deriving the
 * timestamp through the repo timestamp helper.
 *
 * @param currentIso - ISO 8601 timestamp string; defaults to current time via
 * `nowIso()`.
 * @param token - Random token string; defaults to an 8-character secure ID.
 * @returns Agent configuration version identifier.
 */
export function createAgentConfigVersionId(
  currentIso: string = nowIso(),
  token: string = secureId(VERSION_ID_RANDOM_LENGTH)
): string {
  const epochSeconds = Math.floor(Date.parse(currentIso) / 1000);
  return `v${epochSeconds}_${token}`;
}
