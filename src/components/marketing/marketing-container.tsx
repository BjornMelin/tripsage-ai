/**
 * @fileoverview Shared container sizing for marketing pages.
 */

import type * as React from "react";
import { cn } from "@/lib/utils";

export const MARKETING_CONTAINER_CLASS =
  "mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8";

export interface MarketingContainerProps extends React.HTMLAttributes<HTMLDivElement> {}

export function MarketingContainer({ className, ...props }: MarketingContainerProps) {
  return <div className={cn(MARKETING_CONTAINER_CLASS, className)} {...props} />;
}
