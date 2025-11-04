/**
 * @fileoverview AI Elements Response component.
 * Renders markdown content using Streamdown with sensible defaults.
 */
"use client";

import { type ComponentProps, memo } from "react";
import { Streamdown } from "streamdown";
import { cn } from "@/lib/utils";

/** Props for the Response component. */
export type ResponseProps = ComponentProps<typeof Streamdown>;

/**
 * Response renders markdown content (with streaming-friendly parsing).
 *
 * Example:
 *   <Response>{"**Hello** world"}</Response>
 */
export const Response = memo(
  ({ className, ...props }: ResponseProps) => (
    <Streamdown
      className={cn(
        "prose dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        className
      )}
      {...props}
    />
  ),
  (prev, next) => prev.children === next.children
);

Response.displayName = "Response";
