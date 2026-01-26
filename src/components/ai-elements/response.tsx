/**
 * @fileoverview AI Elements Response component. Renders markdown content using Streamdown with sensible defaults.
 */

"use client";

import { type ComponentProps, memo } from "react";
import { Markdown } from "@/components/markdown/Markdown";
import { cn } from "@/lib/utils";

/** Props for the Response component. */
export type ResponseProps = Omit<ComponentProps<typeof Markdown>, "content"> & {
  children: string;
  /**
   * When true, disables interactive controls during streaming.
   * Mode defaults to "streaming" when not explicitly provided.
   */
  isAnimating?: boolean;
};

/**
 * Response renders markdown content (with streaming-friendly parsing).
 *
 * Example:
 *   <Response>{"**Hello** world"}</Response>
 */
export const Response = memo(
  ({
    className,
    children,
    isAnimating,
    mode,
    securityProfile,
    ...props
  }: ResponseProps) => (
    <Markdown
      className={cn(
        "streamdown-chat prose dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        className
      )}
      content={children}
      isAnimating={isAnimating}
      mode={mode ?? "streaming"}
      securityProfile={securityProfile}
      {...props}
    />
  )
);

Response.displayName = "Response";
