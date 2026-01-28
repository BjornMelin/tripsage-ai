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
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium tracking-tight text-nowrap select-none transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 [&_svg]:size-3.5 [&_svg]:shrink-0",
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
    VariantProps<typeof BadgeVariants> {}

/**
 * Badge component for displaying content in a badge-like format.
 *
 * @param className - Optional extra classes.
 * @param variant - Variant of the badge.
 * @returns A styled div element with badge appearance.
 */
function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div
      data-slot="badge"
      className={cn(BadgeVariants({ variant }), className)}
      {...props}
    />
  );
}

/**
 * Export the Badge component and variants.
 *
 * @returns An object containing the Badge component and variants.
 */
export { Badge, BadgeVariants };
