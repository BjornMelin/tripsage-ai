/**
 * @fileoverview Progress bar component built on Radix UI primitives, providing accessible progress indicators with customizable styling and smooth animations.
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
 * @param value - Current progress value (0-max). Use `null` for indeterminate.
 * @param props - Additional props passed to the Radix Progress component.
 * @param ref - Forwarded ref to the progress root element.
 * @returns The Progress component.
 */
export const Progress = React.forwardRef<
  React.ComponentRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(function Progress({ className, value, ...props }, ref) {
  const max = props.max ?? 100;
  const isIndeterminate = value == null;

  const clampedValue = isIndeterminate ? undefined : Math.max(0, Math.min(max, value));
  const percent = isIndeterminate
    ? undefined
    : Math.round(((clampedValue ?? 0) / max) * 100);

  const ariaValueText =
    props["aria-valuetext"] ??
    (isIndeterminate
      ? "Loading"
      : percent !== undefined
        ? `${percent} percent`
        : undefined);

  return (
    <ProgressPrimitive.Root
      ref={ref}
      value={value}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-primary/20",
        className
      )}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={clampedValue}
      aria-valuetext={ariaValueText}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className={cn(
          "h-full flex-1 bg-primary",
          isIndeterminate
            ? "w-1/2 animate-[progress-indeterminate_1.5s_ease-in-out_infinite]"
            : "w-full transition-transform"
        )}
        style={
          isIndeterminate
            ? undefined
            : { transform: `translateX(-${100 - (percent ?? 0)}%)` }
        }
      />
    </ProgressPrimitive.Root>
  );
});
Progress.displayName = ProgressPrimitive.Root.displayName;
