/**
 * @fileoverview Thin wrapper around TanStack Query's HydrationBoundary.
 */

"use client";

import {
  type DehydratedState,
  HydrationBoundary as TanStackHydrationBoundary,
} from "@tanstack/react-query";
import type { ReactNode } from "react";

export function HydrationBoundary({
  children,
  state,
}: {
  children: ReactNode;
  state: DehydratedState;
}) {
  return (
    <TanStackHydrationBoundary state={state}>{children}</TanStackHydrationBoundary>
  );
}
