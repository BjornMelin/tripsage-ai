"use client";

import React from "react";
import { cn } from "@/lib/utils";
import {
  skeletonPropsSchema,
  type SkeletonProps,
} from "@/lib/schemas/error-boundary";

const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  (
    { className, variant = "default", width, height, count = 1, ...props },
    ref
  ) => {
    // Validate props with Zod schema
    const validatedProps = skeletonPropsSchema.parse({
      className,
      variant,
      width,
      height,
      count,
    });

    const baseClasses = "animate-pulse bg-muted";

    const variantClasses = {
      default: "rounded-md",
      circular: "rounded-full",
      rectangular: "rounded-none",
      text: "rounded-sm h-4",
    };

    const skeletonStyle: React.CSSProperties = {
      width: validatedProps.width,
      height: validatedProps.height,
    };

    // Single skeleton
    if (validatedProps.count === 1) {
      return (
        <div
          ref={ref}
          className={cn(
            baseClasses,
            variantClasses[validatedProps.variant || "default"],
            validatedProps.className
          )}
          style={skeletonStyle}
          role="status"
          aria-label="Loading..."
          {...props}
        />
      );
    }

    // Multiple skeletons
    return (
      <div className="space-y-2" role="status" aria-label="Loading...">
        {Array.from({ length: validatedProps.count }).map((_, index) => (
          <div
            key={index}
            className={cn(
              baseClasses,
              variantClasses[validatedProps.variant || "default"],
              validatedProps.className
            )}
            style={skeletonStyle}
          />
        ))}
      </div>
    );
  }
);

Skeleton.displayName = "Skeleton";

// Predefined skeleton components for common use cases
export const SkeletonText = ({
  lines = 3,
  className,
  ...props
}: { lines?: number; className?: string }) => (
  <div className={cn("space-y-2", className)} {...props}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        variant="text"
        className={cn("h-4", i === lines - 1 ? "w-3/4" : "w-full")}
      />
    ))}
  </div>
);

export const SkeletonCard = ({
  className,
  ...props
}: { className?: string }) => (
  <div className={cn("space-y-3", className)} {...props}>
    <Skeleton variant="rectangular" className="h-48 w-full" />
    <div className="space-y-2">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  </div>
);

export const SkeletonAvatar = ({
  size = "md",
  className,
}: { size?: "sm" | "md" | "lg"; className?: string }) => {
  const sizeClasses = {
    sm: "h-8 w-8",
    md: "h-12 w-12",
    lg: "h-16 w-16",
  };

  return (
    <Skeleton variant="circular" className={cn(sizeClasses[size], className)} />
  );
};

export const SkeletonButton = ({
  className,
  ...props
}: { className?: string }) => (
  <Skeleton className={cn("h-10 w-24 rounded-md", className)} {...props} />
);

export const SkeletonTable = ({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) => (
  <div className={cn("space-y-3", className)}>
    {/* Header */}
    <div className="flex space-x-4">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton key={`header-${i}`} className="h-4 w-full" />
      ))}
    </div>

    {/* Rows */}
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div key={`row-${rowIndex}`} className="flex space-x-4">
        {Array.from({ length: columns }).map((_, colIndex) => (
          <Skeleton
            key={`cell-${rowIndex}-${colIndex}`}
            className="h-8 w-full"
          />
        ))}
      </div>
    ))}
  </div>
);

export { Skeleton };
