/**
 * @fileoverview Loading spinner components with multiple visual variants including
 * default spinning circle, animated dots, bars, and pulsing circle styles,
 * supporting different sizes and colors with accessibility features.
 */

import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Loading spinner variants for different styles and sizes using class-variance-authority.
 * Colors aligned with statusVariants semantics:
 * - info: blue-700 (matches statusVariants info)
 * - success: green-700 (matches statusVariants active/success)
 * - warning: amber-700 (matches statusVariants pending/medium)
 * - destructive: red-700 (matches statusVariants error)
 */
const SpinnerVariants = cva("animate-spin", {
  defaultVariants: {
    color: "default",
    size: "md",
  },
  variants: {
    color: {
      default: "text-primary",
      destructive: "text-red-700",
      info: "text-blue-700",
      muted: "text-muted-foreground",
      success: "text-green-700",
      warning: "text-amber-700",
      white: "text-white",
    },
    size: {
      lg: "h-8 w-8",
      md: "h-6 w-6",
      sm: "h-4 w-4",
      xl: "h-12 w-12",
    },
  },
});

/**
 * Props interface for the LoadingSpinner component.
 */
export interface LoadingSpinnerProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "color">,
    VariantProps<typeof SpinnerVariants> {
  /** Visual variant of the spinner. */
  variant?: "default" | "dots" | "bars" | "pulse";
}

/**
 * Props interface for SVG-based spinner components.
 */
export interface SVGSpinnerProps
  extends Omit<React.SVGAttributes<SVGSVGElement>, "color">,
    VariantProps<typeof SpinnerVariants> {
  /** Visual variant of the spinner. */
  variant?: "default" | "dots" | "bars" | "pulse";
}

/**
 * Default spinning circle loader component with animated SVG path.
 *
 * @param props - Component props including size, color, and HTML attributes.
 * @param ref - Forwarded ref to the spinner container div.
 * @returns The default spinner component.
 */
const DefaultSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size, color, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(SpinnerVariants({ color, size }), className)}
      role="status"
      aria-label="Loading"
      {...props}
    >
      <svg
        className="w-full h-full"
        fill="none"
        viewBox="0 0 24 24"
        role="status"
        aria-label="Loading"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </div>
  )
);

DefaultSpinner.displayName = "DefaultSpinner";

/**
 * Animated dots loader component with staggered pulse animations.
 *
 * @param props - Component props including size, color, and HTML attributes.
 * @param ref - Forwarded ref to the spinner container div.
 * @returns The dots spinner component.
 */
const DotsSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size, color, className, ...props }, ref) => {
    const dotSizes = {
      lg: "h-2 w-2",
      md: "h-1.5 w-1.5",
      sm: "h-1 w-1",
      xl: "h-3 w-3",
    };

    const dotSize = dotSizes[size || "md"];

    return (
      <div
        ref={ref}
        className={cn("flex space-x-1", className)}
        role="status"
        aria-label="Loading"
        {...props}
      >
        {[0, 1, 2].map((index) => (
          <div
            key={`dot-${index}`}
            className={cn(
              "animate-pulse rounded-full bg-current dots-spinner",
              dotSize,
              SpinnerVariants({ color })
            )}
            style={{
              animationDelay: `${index * 0.15}s`,
              animationDuration: "0.6s",
            }}
          />
        ))}
      </div>
    );
  }
);

DotsSpinner.displayName = "DotsSpinner";

/**
 * Animated bars loader component with sequential pulse animations.
 *
 * @param props - Component props including size, color, and HTML attributes.
 * @param ref - Forwarded ref to the spinner container div.
 * @returns The bars spinner component.
 */
const BarsSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size, color, className, ...props }, ref) => {
    const barSizes = {
      lg: "h-6 w-1",
      md: "h-4 w-0.5",
      sm: "h-3 w-0.5",
      xl: "h-8 w-1",
    };

    const barSize = barSizes[size || "md"];

    return (
      <div
        ref={ref}
        className={cn("flex items-center space-x-0.5", className)}
        role="status"
        aria-label="Loading"
        {...props}
      >
        {[0, 1, 2, 3, 4].map((index) => (
          <div
            key={`bar-${index}`}
            className={cn(
              "animate-pulse rounded-full bg-current bars-spinner",
              barSize,
              SpinnerVariants({ color })
            )}
            style={{
              animationDelay: `${index * 0.1}s`,
              animationDuration: "1s",
            }}
          />
        ))}
      </div>
    );
  }
);

BarsSpinner.displayName = "BarsSpinner";

/**
 * Pulsing circle loader component with continuous ping animation.
 *
 * @param props - Component props including size, color, and HTML attributes.
 * @param ref - Forwarded ref to the spinner container div.
 * @returns The pulse spinner component.
 */
const PulseSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size, color, className, ...props }, ref) => {
    const pulseSizes = {
      lg: "h-8 w-8",
      md: "h-6 w-6",
      sm: "h-4 w-4",
      xl: "h-12 w-12",
    };

    const pulseSize = pulseSizes[size || "md"];

    return (
      <div
        ref={ref}
        className={cn(
          "animate-ping rounded-full bg-current opacity-75",
          pulseSize,
          SpinnerVariants({ color }),
          className
        )}
        role="status"
        aria-label="Loading"
        {...props}
      />
    );
  }
);

PulseSpinner.displayName = "PulseSpinner";

/**
 * Main Loading Spinner component that renders different spinner variants.
 *
 * Supports multiple visual styles: default (spinning circle), dots, bars, and pulse.
 * All variants include accessibility features and support size/color customization.
 *
 * @param variant - The visual variant of the spinner to render.
 * @param props - Additional props passed to the specific spinner variant.
 * @param ref - Forwarded ref to the spinner component.
 * @returns The appropriate spinner component based on variant.
 */
const LoadingSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ variant = "default", ...props }, ref) => {
    switch (variant) {
      case "dots":
        return <DotsSpinner ref={ref} {...props} />;
      case "bars":
        return <BarsSpinner ref={ref} {...props} />;
      case "pulse":
        return <PulseSpinner ref={ref} {...props} />;
      default:
        return <DefaultSpinner ref={ref} {...props} />;
    }
  }
);

LoadingSpinner.displayName = "LoadingSpinner";

export { LoadingSpinner, SpinnerVariants };
