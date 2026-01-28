/**
 * @fileoverview Shared container sizing for marketing pages.
 */

import type * as React from "react";
import { cn } from "@/lib/utils";

/** Base layout classes for marketing page containers. */
export const MARKETING_CONTAINER_CLASS =
  "mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8";

/** Props for the marketing container wrapper. */
export interface MarketingContainerProps extends React.HTMLAttributes<HTMLDivElement> {}

/** Renders a marketing container with shared sizing and padding. */
export function MarketingContainer({ className, ...props }: MarketingContainerProps) {
  return <div className={cn(MARKETING_CONTAINER_CLASS, className)} {...props} />;
}
