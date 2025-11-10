/**
 * @fileoverview Skeleton component with accessibility support and customizable variants.
 */

import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Skeleton component variants for consistent styling
 */
const SkeletonVariants = cva("rounded-md bg-muted", {
  defaultVariants: {
    animation: "pulse",
    variant: "default",
  },
  variants: {
    animation: {
      none: "",
      pulse: "animate-pulse",
      wave: "animate-[wave_1.5s_ease-in-out_infinite]",
    },
    variant: {
      default: "bg-slate-100 dark:bg-slate-800",
      light: "bg-slate-50 dark:bg-slate-700",
      medium: "bg-slate-200 dark:bg-slate-600",
      rounded: "rounded-full",
    },
  },
});

export interface SkeletonProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof SkeletonVariants> {
  width?: string | number;
  height?: string | number;
  lines?: number;
  animate?: boolean;
}

/**
 * Basic skeleton component with accessibility support
 */
export const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  (
    {
      className,
      variant,
      animation,
      width,
      height,
      lines = 1,
      animate = true,
      style,
      ...props
    },
    ref
  ) => {
    // Calculate final animation variant
    const finalAnimation = animate === false ? "none" : animation;

    // Build inline styles
    const inlineStyles: React.CSSProperties = {
      height: typeof height === "number" ? `${height}px` : height,
      width: typeof width === "number" ? `${width}px` : width,
      ...style,
    };

    // Single line skeleton
    if (lines === 1) {
      return (
        <div
          ref={ref}
          className={cn(
            SkeletonVariants({ animation: finalAnimation, variant }),
            "skeleton",
            className
          )}
          style={inlineStyles}
          role="status"
          aria-label="Loading content..."
          {...props}
        />
      );
    }

    // Multi-line skeleton
    return (
      <div
        ref={ref}
        className={cn("space-y-2", className)}
        role="status"
        aria-label="Loading content..."
        {...props}
      >
        {Array.from({ length: lines }).map((_, index) => {
          // Vary the width of lines to look more natural
          const lineWidth = index === lines - 1 ? "75%" : "100%";

          return (
            <div
              key={`skeleton-line-${index}-${lines}`}
              className={cn(
                SkeletonVariants({ animation: finalAnimation, variant }),
                "skeleton"
              )}
              style={{
                height: inlineStyles.height || "1rem",
                width: lineWidth,
              }}
            />
          );
        })}
      </div>
    );
  }
);

Skeleton.displayName = "Skeleton";
export { SkeletonVariants };
