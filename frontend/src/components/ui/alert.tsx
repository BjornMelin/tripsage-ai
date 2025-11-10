/**
 * @fileoverview Alert component for displaying content in an alert-like format.
 * Provides a styled alert with various sizes and variants.
 */
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Variants for alert components.
 *
 * @returns A string of classes for the alert.
 */
const AlertVariants = cva(
  "relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground",
  {
    defaultVariants: {
      variant: "default",
    },
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive:
          "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive",
      },
    },
  }
);

/**
 * Alert component for displaying content in an alert-like format.
 *
 * @param className Optional extra classes.
 * @param variant Variant of the alert.
 * @returns A div with alert styling and ARIA role.
 */
export const Alert = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof AlertVariants>
>(function Alert({ className, variant, ...props }, ref) {
  return (
    <div
      ref={ref}
      role="alert"
      className={cn(AlertVariants({ variant }), className)}
      {...props}
    />
  );
});
Alert.displayName = "Alert";

/**
 * Alert title component for displaying content in an alert-like format.
 *
 * @param className Optional extra classes.
 * @returns A h5 with alert title styling and ARIA role.
 */
export const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(function AlertTitle({ className, ...props }, ref) {
  return (
    <h5
      ref={ref}
      className={cn("mb-1 font-medium leading-none tracking-tight", className)}
      {...props}
    />
  );
});
AlertTitle.displayName = "AlertTitle";

/**
 * Alert description component for displaying content in an alert-like format.
 *
 * @param className Optional extra classes.
 * @returns A div with alert description styling and ARIA role.
 */
export const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(function AlertDescription({ className, ...props }, ref) {
  return (
    <div
      ref={ref}
      className={cn("text-sm [&_p]:leading-relaxed", className)}
      {...props}
    />
  );
});
AlertDescription.displayName = "AlertDescription";
