/**
 * @fileoverview AI Elements Sources components.
 * Minimal implementation using shadcn/ui Popover primitives.
 */

"use client";

import type * as React from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export type SourcesProps = React.ComponentPropsWithoutRef<typeof Popover>;

/**
 * Sources is a container that groups a trigger and content listing citations.
 */
export function Sources(props: SourcesProps) {
  return <Popover {...props} />;
}

export interface SourcesTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Optional count to show in the trigger label. */
  count?: number;
}

/**
 * SourcesTrigger renders a small button to open the sources popover.
 */
export function SourcesTrigger({
  count,
  className,
  children,
  ...props
}: SourcesTriggerProps) {
  return (
    <PopoverTrigger asChild>
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-2 rounded-md border bg-background px-2 py-1 text-xs shadow-sm hover:bg-accent",
          className
        )}
        aria-label="Show sources"
        {...props}
      >
        {children ?? (
          <span>{count != null ? `Using ${count} sources` : "Sources"}</span>
        )}
      </button>
    </PopoverTrigger>
  );
}

export type SourcesContentProps = React.ComponentPropsWithoutRef<typeof PopoverContent>;

/**
 * SourcesContent lists provided citations.
 */
export function SourcesContent({ className, ...props }: SourcesContentProps) {
  return (
    <PopoverContent
      className={cn("w-96 p-3 text-sm", className)}
      align="end"
      sideOffset={8}
      {...props}
    />
  );
}

export interface SourceProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {}

/**
 * Source renders a single source link item.
 */
export function Source({ className, children, ...props }: SourceProps) {
  return (
    <a
      className={cn(
        "block truncate rounded px-2 py-1 text-foreground/80 underline-offset-4 hover:underline",
        className
      )}
      target="_blank"
      rel="noreferrer noopener"
      {...props}
    >
      {children ?? props.href}
    </a>
  );
}
