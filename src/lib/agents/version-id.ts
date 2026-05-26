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
 * @returns Agent configuration version identifier.
 */
export function createAgentConfigVersionId(
  currentIso: string = nowIso(),
  token: string = secureId(VERSION_ID_RANDOM_LENGTH)
): string {
  const epochSeconds = Math.floor(Date.parse(currentIso) / 1000);
  return `v${epochSeconds}_${token}`;
}
