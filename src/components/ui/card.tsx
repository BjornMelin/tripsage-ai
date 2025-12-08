/**
 * @fileoverview Card component for displaying content in a card-like format.
 * Provides a styled card with header, title, description, content, and footer.
 */
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Card component for displaying content in a card-like format.
 *
 * @param className Optional extra classes.
 * @returns A div with card styling and ARIA role.
 */
export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(function Card({ className, ...props }, ref) {
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-lg border bg-card text-card-foreground shadow-sm",
        className
      )}
      {...props}
    />
  );
});
Card.displayName = "Card";

/**
 * Card header component for displaying content in a card-like format.
 *
 * @param className Optional extra classes.
 * @returns A div with card header styling and ARIA role.
 */
export const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(function CardHeader({ className, ...props }, ref) {
  return (
    <div
      ref={ref}
      className={cn("flex flex-col space-y-1.5 p-6", className)}
      {...props}
    />
  );
});
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(function CardTitle({ className, ...props }, ref) {
  return (
    <h3
      ref={ref}
      className={cn("text-2xl font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  );
});
CardTitle.displayName = "CardTitle";

/**
 * Card description component for displaying content in a card-like format.
 *
 * @param className Optional extra classes.
 * @returns A p with card description styling and ARIA role.
 */
export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(function CardDescription({ className, ...props }, ref) {
  return (
    <p
      ref={ref}
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
});
CardDescription.displayName = "CardDescription";

/**
 * Card content component for displaying content in a card-like format.
 *
 * @param className Optional extra classes.
 * @returns A div with card content styling and ARIA role.
 */
export const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(function CardContent({ className, ...props }, ref) {
  return <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />;
});
CardContent.displayName = "CardContent";

/**
 * Card footer component for displaying content in a card-like format.
 *
 * @param className Optional extra classes.
 * @returns A div with card footer styling and ARIA role.
 */
export const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(function CardFooter({ className, ...props }, ref) {
  return (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  );
});
CardFooter.displayName = "CardFooter";
