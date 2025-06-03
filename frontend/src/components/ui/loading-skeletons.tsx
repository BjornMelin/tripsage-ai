import { cn } from "@/lib/utils";
import * as React from "react";
import { Skeleton } from "./skeleton";

/**
 * Avatar skeleton component
 */
export interface AvatarSkeletonProps {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

export const AvatarSkeleton = React.forwardRef<HTMLDivElement, AvatarSkeletonProps>(
  ({ size = "md", className, ...props }, ref) => {
    const sizeClasses = {
      sm: "h-8 w-8",
      md: "h-10 w-10",
      lg: "h-12 w-12",
      xl: "h-16 w-16",
    };

    return (
      <Skeleton
        ref={ref}
        variant="rounded"
        className={cn(sizeClasses[size], className)}
        aria-label="Loading profile picture"
        {...props}
      />
    );
  }
);

AvatarSkeleton.displayName = "AvatarSkeleton";

/**
 * Card skeleton component
 */
export interface CardSkeletonProps {
  hasImage?: boolean;
  hasAvatar?: boolean;
  titleLines?: number;
  bodyLines?: number;
  className?: string;
}

export const CardSkeleton = React.forwardRef<HTMLDivElement, CardSkeletonProps>(
  (
    {
      hasImage = false,
      hasAvatar = false,
      titleLines = 1,
      bodyLines = 3,
      className,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn("rounded-lg border p-4 space-y-3", className)}
        role="status"
        aria-label="Loading card content"
        {...props}
      >
        {/* Image placeholder */}
        {hasImage && <Skeleton className="h-48 w-full rounded-md" />}

        {/* Header with optional avatar */}
        <div className="flex items-center space-x-3">
          {hasAvatar && <AvatarSkeleton size="sm" />}
          <div className="space-y-2 flex-1">
            <Skeleton lines={titleLines} height="1.25rem" />
          </div>
        </div>

        {/* Body content */}
        {bodyLines > 0 && (
          <div className="space-y-2">
            <Skeleton lines={bodyLines} height="1rem" />
          </div>
        )}
      </div>
    );
  }
);

CardSkeleton.displayName = "CardSkeleton";

/**
 * List item skeleton component
 */
export interface ListItemSkeletonProps {
  hasAvatar?: boolean;
  hasAction?: boolean;
  titleLines?: number;
  subtitleLines?: number;
  className?: string;
}

export const ListItemSkeleton = React.forwardRef<HTMLDivElement, ListItemSkeletonProps>(
  (
    {
      hasAvatar = false,
      hasAction = false,
      titleLines = 1,
      subtitleLines = 1,
      className,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn("flex items-center justify-between p-3 space-x-3", className)}
        role="status"
        aria-label="Loading list item"
        {...props}
      >
        <div className="flex items-center space-x-3 flex-1">
          {hasAvatar && <AvatarSkeleton size="sm" />}
          <div className="space-y-1 flex-1">
            <Skeleton lines={titleLines} height="1.125rem" />
            {subtitleLines > 0 && (
              <Skeleton lines={subtitleLines} height="0.875rem" width="80%" />
            )}
          </div>
        </div>

        {hasAction && <Skeleton className="h-8 w-16 rounded-md" />}
      </div>
    );
  }
);

ListItemSkeleton.displayName = "ListItemSkeleton";

/**
 * Table skeleton component
 */
export interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  hasHeader?: boolean;
  className?: string;
}

export const TableSkeleton = React.forwardRef<HTMLTableElement, TableSkeletonProps>(
  ({ rows = 5, columns = 4, hasHeader = true, className, ...props }, ref) => {
    return (
      <div className={cn("overflow-hidden rounded-md border", className)}>
        <table
          ref={ref}
          className="w-full"
          role="status"
          aria-label="Loading table data"
          {...props}
        >
          {hasHeader && (
            <thead className="border-b bg-muted/50">
              <tr>
                {Array.from({ length: columns }).map((_, index) => (
                  <th key={index} className="p-3">
                    <Skeleton height="1rem" width="80%" />
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {Array.from({ length: rows }).map((_, rowIndex) => (
              <tr key={rowIndex} className="border-b last:border-0">
                {Array.from({ length: columns }).map((_, colIndex) => (
                  <td key={colIndex} className="p-3">
                    <Skeleton height="1rem" width={colIndex === 0 ? "90%" : "70%"} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
);

TableSkeleton.displayName = "TableSkeleton";

/**
 * Form skeleton component
 */
export interface FormSkeletonProps {
  fields?: number;
  hasSubmitButton?: boolean;
  className?: string;
}

export const FormSkeleton = React.forwardRef<HTMLDivElement, FormSkeletonProps>(
  ({ fields = 3, hasSubmitButton = true, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("space-y-4", className)}
        role="status"
        aria-label="Loading form"
        {...props}
      >
        {Array.from({ length: fields }).map((_, index) => (
          <div key={index} className="space-y-2">
            <Skeleton height="1rem" width="25%" />
            <Skeleton height="2.5rem" width="100%" className="rounded-md" />
          </div>
        ))}

        {hasSubmitButton && (
          <div className="pt-2">
            <Skeleton height="2.5rem" width="120px" className="rounded-md" />
          </div>
        )}
      </div>
    );
  }
);

FormSkeleton.displayName = "FormSkeleton";

/**
 * Chart/Graph skeleton component
 */
export interface ChartSkeletonProps {
  type?: "bar" | "line" | "pie" | "area";
  className?: string;
}

export const ChartSkeleton = React.forwardRef<HTMLDivElement, ChartSkeletonProps>(
  ({ type = "bar", className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("p-4 space-y-4", className)}
        role="status"
        aria-label="Loading chart data"
        {...props}
      >
        {/* Chart title */}
        <Skeleton height="1.5rem" width="40%" />

        {/* Chart area */}
        <div className="relative h-48 w-full">
          {type === "bar" && (
            <div className="flex items-end justify-around h-full space-x-2">
              {Array.from({ length: 8 }).map((_, index) => (
                <Skeleton
                  key={index}
                  width="12%"
                  height={`${Math.random() * 60 + 40}%`}
                  className="rounded-t-sm"
                />
              ))}
            </div>
          )}

          {type === "line" && (
            <div className="relative h-full w-full">
              <Skeleton height="100%" width="100%" className="rounded-md" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-full h-0.5 bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent transform -rotate-12" />
              </div>
            </div>
          )}

          {type === "pie" && (
            <div className="flex items-center justify-center h-full">
              <Skeleton variant="rounded" className="h-32 w-32" />
            </div>
          )}

          {type === "area" && (
            <div className="relative h-full w-full">
              <Skeleton height="100%" width="100%" className="rounded-md" />
              <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-gradient-to-t from-muted/50 to-transparent rounded-b-md" />
            </div>
          )}
        </div>

        {/* Chart legend */}
        <div className="flex flex-wrap gap-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="flex items-center space-x-2">
              <Skeleton className="h-3 w-3 rounded-sm" />
              <Skeleton height="0.875rem" width="60px" />
            </div>
          ))}
        </div>
      </div>
    );
  }
);

ChartSkeleton.displayName = "ChartSkeleton";
