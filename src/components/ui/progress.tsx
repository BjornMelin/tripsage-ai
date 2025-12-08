/**
 * @fileoverview Progress bar component built on Radix UI primitives, providing
 * accessible progress indicators with customizable styling and smooth animations.
 */

"use client";

import * as ProgressPrimitive from "@radix-ui/react-progress";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Progress bar component for displaying completion status.
 *
 * Built on Radix UI Progress primitive with accessibility features including
 * ARIA attributes and screen reader support. Supports custom styling and smooth transitions.
 *
 * @param className - Additional CSS classes to apply.
 * @param value - Current progress value (0-100).
 * @param props - Additional props passed to the Radix Progress component.
 * @param ref - Forwarded ref to the progress root element.
 * @returns The Progress component.
 */
export const Progress = React.forwardRef<
  React.ComponentRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(function Progress({ className, value, ...props }, ref) {
  return (
    <ProgressPrimitive.Root
      ref={ref}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-primary/20",
        className
      )}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value || 0)}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className="h-full w-full flex-1 bg-primary transition-all"
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </ProgressPrimitive.Root>
  );
});
Progress.displayName = ProgressPrimitive.Root.displayName;
