/**
 * @fileoverview Next.js build-phase detection shared across server/client.
 */

import { PHASE_EXPORT, PHASE_PRODUCTION_BUILD } from "next/constants";

/**
 * Check if we're in Next.js build or export phase.
 */
export function isBuildPhase(): boolean {
  return (
    process.env.NEXT_PHASE === PHASE_PRODUCTION_BUILD ||
    process.env.NEXT_PHASE === PHASE_EXPORT
  );
}
