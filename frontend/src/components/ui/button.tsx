/**
 * @fileoverview Button component with variant styling. When `asChild` is true,
 * styles are merged into the single child element (e.g., Next.js `Link`) to
 * avoid additional wrappers and invalid nested anchors.
 */

import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        success: "bg-success text-success-foreground hover:bg-success/90",
        warning: "bg-warning text-warning-foreground hover:bg-warning/90",
        info: "bg-info text-info-foreground hover:bg-info/90",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

/**
 * Variant class generator for Button.
 * @returns A class name string for the given `variant` and `size`.
 */

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /**
   * When true, renders the child element directly with button styles
   * merged into it. Intended for components like `Link` that should be
   * styled like a button without additional wrappers.
   */
  asChild?: boolean;
}

/**
 * Button component.
 * @param props Component props including `variant`, `size`, and `asChild`.
 * @returns A styled `<button>` or the child element when `asChild` is true.
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    if (asChild) {
      return (
        <React.Fragment>
          {React.Children.map(props.children, (child) => {
            if (React.isValidElement(child)) {
              // Avoid forwarding `children` from Button props into the cloned
              // child. Passing `children` would re-nest the child element and
              // can create invalid nested anchors when used with `Link`.
              // Only forward non-children props we want to apply to the child.
              const { children: _ignored, ...restProps } = props;
              return React.cloneElement(
                child as React.ReactElement<{ className?: string }>,
                {
                  ...restProps,
                  className: cn(
                    buttonVariants({ variant, size }),
                    className,
                    (child.props as { className?: string }).className
                  ),
                }
              );
            }
            return child;
          })}
        </React.Fragment>
      );
    }

    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
