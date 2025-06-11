import { cn } from "@/lib/utils";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

/**
 * Loading spinner variants for different styles and sizes
 */
const spinnerVariants = cva("animate-spin", {
  variants: {
    size: {
      sm: "h-4 w-4",
      md: "h-6 w-6",
      lg: "h-8 w-8",
      xl: "h-12 w-12",
    },
    color: {
      default: "text-primary",
      white: "text-white",
      muted: "text-muted-foreground",
      destructive: "text-destructive",
      success: "text-green-600",
      warning: "text-yellow-600",
      info: "text-blue-600",
    },
  },
  defaultVariants: {
    size: "md",
    color: "default",
  },
});

export interface LoadingSpinnerProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "color">,
    VariantProps<typeof spinnerVariants> {
  variant?: "default" | "dots" | "bars" | "pulse";
}

export interface SVGSpinnerProps
  extends Omit<React.SVGAttributes<SVGSVGElement>, "color">,
    VariantProps<typeof spinnerVariants> {
  variant?: "default" | "dots" | "bars" | "pulse";
}

/**
 * Default spinning circle loader
 */
const DefaultSpinner = ({ size, color, className }: LoadingSpinnerProps) => (
  <div className={cn(spinnerVariants({ size, color }), className)}>
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
);

DefaultSpinner.displayName = "DefaultSpinner";

/**
 * Animated dots loader
 */
const DotsSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size, color, className, ...props }, ref) => {
    const dotSizes = {
      sm: "h-1 w-1",
      md: "h-1.5 w-1.5",
      lg: "h-2 w-2",
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
            key={index}
            className={cn(
              "animate-pulse rounded-full bg-current dots-spinner",
              dotSize,
              spinnerVariants({ color })
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
 * Animated bars loader
 */
const BarsSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size, color, className, ...props }, ref) => {
    const barSizes = {
      sm: "h-3 w-0.5",
      md: "h-4 w-0.5",
      lg: "h-6 w-1",
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
            key={index}
            className={cn(
              "animate-pulse rounded-full bg-current bars-spinner",
              barSize,
              spinnerVariants({ color })
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
 * Pulsing circle loader
 */
const PulseSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size, color, className, ...props }, ref) => {
    const pulseSizes = {
      sm: "h-4 w-4",
      md: "h-6 w-6",
      lg: "h-8 w-8",
      xl: "h-12 w-12",
    };

    const pulseSize = pulseSizes[size || "md"];

    return (
      <div
        ref={ref}
        className={cn(
          "animate-ping rounded-full bg-current opacity-75",
          pulseSize,
          spinnerVariants({ color }),
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
 * Main Loading Spinner component
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
        return <DefaultSpinner {...props} />;
    }
  }
);

LoadingSpinner.displayName = "LoadingSpinner";

export { LoadingSpinner, spinnerVariants };
