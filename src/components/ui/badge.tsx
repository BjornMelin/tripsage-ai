/**
 * @fileoverview Badge component for displaying content in a badge-like format. Provides a styled badge with various sizes and variants.
 */

import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Variants for badge components.
 */
const BadgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium tracking-tight transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 [&_svg]:size-3.5 [&_svg]:shrink-0",
  {
    defaultVariants: {
      variant: "default",
    },
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-xs hover:bg-destructive/90",
        ghost:
          "border-foreground/10 bg-muted/40 text-foreground shadow-xs hover:bg-muted/55 supports-[backdrop-filter]:bg-muted/30 supports-[backdrop-filter]:backdrop-blur",
        highlight:
          "border-highlight/25 bg-highlight/10 text-foreground shadow-xs hover:bg-highlight/15",
        outline:
          "border-foreground/10 bg-background/50 text-foreground shadow-xs hover:bg-muted/35 supports-[backdrop-filter]:bg-background/40 supports-[backdrop-filter]:backdrop-blur",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80",
      },
    },
  }
);

/**
 * Props for the Badge component.
 */
export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof BadgeVariants> {
  isDecorative?: boolean;
  truncate?: boolean;
}

/**
 * Badge component for displaying content in a badge-like format.
 *
 * @param className - Optional extra classes for the badge.
 * @param isDecorative - When true, marks the badge as decorative and disables text selection.
 * @param truncate - When true, truncates overflowing text with an ellipsis.
 * @param variant - Visual variant of the badge.
 * @param props - Additional div attributes passed to the root element.
 * @returns A styled div element with badge appearance.
 */
function Badge({ className, isDecorative, truncate, variant, ...props }: BadgeProps) {
  return (
    <div
      data-slot="badge"
      className={cn(
        BadgeVariants({ variant }),
        isDecorative && "select-none",
        truncate && "truncate",
        className
      )}
      {...props}
    />
  );
}

/**
 * Badge component and variant styles for consistent badge rendering.
 */
export { Badge, BadgeVariants };
