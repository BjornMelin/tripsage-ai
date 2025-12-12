/**
 * @fileoverview Next.js build-phase detection shared across server/client.
 */

/**
 * Check if we're in Next.js build or export phase.
 */
export function isBuildPhase(): boolean {
  return (
    process.env.NEXT_PHASE === "phase-production-build" ||
    process.env.NEXT_PHASE === "phase-export"
  );
}
