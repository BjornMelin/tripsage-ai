/**
 * @fileoverview Badge component for displaying content in a badge-like format.
 * Provides a styled badge with various sizes and variants.
 */
import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Variants for badge components.
 *
 * @returns A string of classes for the badge.
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    defaultVariants: {
      variant: "default",
    },
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
      },
    },
  }
);

/**
 * Props for the Badge component.
 *
 * @param className Optional extra classes.
 * @param variant Variant of the badge.
 * @returns A div with badge styling and ARIA role.
 */
export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

/**
 * Badge component for displaying content in a badge-like format.
 *
 * @param className Optional extra classes.
 * @param variant Variant of the badge.
 * @returns A div with badge styling and ARIA role.
 */
function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

/**
 * Export the Badge component and variants.
 *
 * @returns An object containing the Badge component and variants.
 */
export { Badge, badgeVariants };
