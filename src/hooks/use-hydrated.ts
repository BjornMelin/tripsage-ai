/**
 * @fileoverview Hydration-safe client readiness signal for SSR client components.
 */

"use client";

import { useSyncExternalStore } from "react";

const SUBSCRIBE_TO_HYDRATION = () => () => undefined;

/**
 * Returns false for the server and initial hydration snapshot, then true on the client.
 *
 * @returns Whether client hydration has completed.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    SUBSCRIBE_TO_HYDRATION,
    () => true,
    () => false
  );
}
