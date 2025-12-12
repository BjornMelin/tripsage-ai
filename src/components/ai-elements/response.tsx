/**
 * @fileoverview AI Elements Response component.
 * Renders markdown content using Streamdown with sensible defaults.
 */
"use client";

import { type ComponentProps, memo } from "react";
import { Streamdown } from "streamdown";
import { cn } from "@/lib/utils";
import {
  streamdownControls,
  streamdownMermaid,
  streamdownRehypePlugins,
  streamdownRemarkPlugins,
  streamdownShikiTheme,
} from "./streamdown-config";

/** Props for the Response component. */
export type ResponseProps = ComponentProps<typeof Streamdown>;

/**
 * Response renders markdown content (with streaming-friendly parsing).
 *
 * Example:
 *   <Response>{"**Hello** world"}</Response>
 */
export const Response = memo(
  ({
    className,
    controls = streamdownControls,
    mermaid = streamdownMermaid,
    mode = "streaming",
    rehypePlugins = streamdownRehypePlugins,
    remarkPlugins = streamdownRemarkPlugins,
    shikiTheme = streamdownShikiTheme,
    ...props
  }: ResponseProps) => (
    <Streamdown
      className={cn(
        "streamdown-chat prose dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        className
      )}
      controls={controls}
      mermaid={mermaid}
      mode={mode}
      rehypePlugins={rehypePlugins}
      remarkPlugins={remarkPlugins}
      shikiTheme={shikiTheme}
      {...props}
    />
  )
);

Response.displayName = "Response";
