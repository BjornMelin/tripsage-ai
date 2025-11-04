/**
 * @fileoverview Loading skeleton components for various UI elements.
 * Provides placeholder components that mimic the layout of actual content
 * during loading states.
 */

import * as React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "./skeleton";

/**
 * Props for the AvatarSkeleton component.
 */
export interface AvatarSkeletonProps {
  /** Size variant for the avatar skeleton. */
  size?: "sm" | "md" | "lg" | "xl";
  /** Optional additional CSS classes. */
  className?: string;
}

/**
 * Avatar skeleton component that displays a circular placeholder for profile images.
 *
 * @param size - Size variant for the avatar skeleton. Defaults to "md".
 * @param className - Optional additional CSS classes.
 * @param props - Additional HTML div element props.
 * @returns A skeleton component styled as a circular avatar placeholder.
 */
export const AvatarSkeleton = React.forwardRef<HTMLDivElement, AvatarSkeletonProps>(
  ({ size = "md", className, ...props }, ref) => {
    const sizeClasses = {
      lg: "h-12 w-12",
      md: "h-10 w-10",
      sm: "h-8 w-8",
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
 * Props for the CardSkeleton component.
 */
export interface CardSkeletonProps {
  /** Whether to include an image placeholder at the top of the card. */
  hasImage?: boolean;
  /** Whether to include an avatar in the header section. */
  hasAvatar?: boolean;
  /** Number of title lines to display. Defaults to 1. */
  titleLines?: number;
  /** Number of body content lines to display. Defaults to 3. */
  bodyLines?: number;
  /** Optional additional CSS classes. */
  className?: string;
}

/**
 * Card skeleton component that displays a placeholder for card-based content.
 *
 * @param hasImage - Whether to include an image placeholder. Defaults to false.
 * @param hasAvatar - Whether to include an avatar. Defaults to false.
 * @param titleLines - Number of title lines. Defaults to 1.
 * @param bodyLines - Number of body lines. Defaults to 3.
 * @param className - Optional additional CSS classes.
 * @param props - Additional HTML div element props.
 * @returns A skeleton component mimicking a content card layout.
 */
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
 * Props for the ListItemSkeleton component.
 */
export interface ListItemSkeletonProps {
  /** Whether to include an avatar at the start of the list item. */
  hasAvatar?: boolean;
  /** Whether to include an action button at the end of the list item. */
  hasAction?: boolean;
  /** Number of title lines to display. Defaults to 1. */
  titleLines?: number;
  /** Number of subtitle lines to display. Defaults to 1. */
  subtitleLines?: number;
  /** Optional additional CSS classes. */
  className?: string;
}

/**
 * List item skeleton component that displays a placeholder for list item content.
 *
 * @param hasAvatar - Whether to include an avatar. Defaults to false.
 * @param hasAction - Whether to include an action button. Defaults to false.
 * @param titleLines - Number of title lines. Defaults to 1.
 * @param subtitleLines - Number of subtitle lines. Defaults to 1.
 * @param className - Optional additional CSS classes.
 * @param props - Additional HTML div element props.
 * @returns A skeleton component mimicking a list item layout.
 */
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
 * Props for the TableSkeleton component.
 */
export interface TableSkeletonProps {
  /** Number of data rows to display. Defaults to 5. */
  rows?: number;
  /** Number of columns to display. Defaults to 4. */
  columns?: number;
  /** Whether to include a header row. Defaults to true. */
  hasHeader?: boolean;
  /** Optional additional CSS classes. */
  className?: string;
}

/**
 * Table skeleton component that displays a placeholder for tabular data.
 *
 * @param rows - Number of data rows. Defaults to 5.
 * @param columns - Number of columns. Defaults to 4.
 * @param hasHeader - Whether to show header row. Defaults to true.
 * @param className - Optional additional CSS classes.
 * @param props - Additional HTML table element props.
 * @returns A skeleton component mimicking a table layout.
 */
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
                  <th key={`table-header-col-${index}`} className="p-3">
                    <Skeleton height="1rem" width="80%" />
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {Array.from({ length: rows }).map((_, rowIndex) => (
              <tr key={`table-row-${rowIndex}`} className="border-b last:border-0">
                {Array.from({ length: columns }).map((_, colIndex) => (
                  <td key={`table-cell-${rowIndex}-${colIndex}`} className="p-3">
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
 * Props for the FormSkeleton component.
 */
export interface FormSkeletonProps {
  /** Number of form fields to display. Defaults to 3. */
  fields?: number;
  /** Whether to include a submit button at the end. Defaults to true. */
  hasSubmitButton?: boolean;
  /** Optional additional CSS classes. */
  className?: string;
}

/**
 * Form skeleton component that displays a placeholder for form layouts.
 *
 * @param fields - Number of form fields. Defaults to 3.
 * @param hasSubmitButton - Whether to show submit button. Defaults to true.
 * @param className - Optional additional CSS classes.
 * @param props - Additional HTML div element props.
 * @returns A skeleton component mimicking a form layout.
 */
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
          <div key={`form-skeleton-field-${index}`} className="space-y-2">
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
 * Props for the ChartSkeleton component.
 */
export interface ChartSkeletonProps {
  /** Type of chart to display skeleton for. Defaults to "bar". */
  type?: "bar" | "line" | "pie" | "area";
  /** Optional additional CSS classes. */
  className?: string;
}

/**
 * Chart skeleton component that displays a placeholder for chart/graph visualizations.
 *
 * @param type - Chart type variant. Defaults to "bar".
 * @param className - Optional additional CSS classes.
 * @param props - Additional HTML div element props.
 * @returns A skeleton component mimicking a chart layout.
 */
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
              {(() => {
                const heights = [40, 55, 65, 50, 70, 45, 60, 52];
                return heights.map((h, index) => (
                  <Skeleton
                    key={`chart-bar-${index}`}
                    width="12%"
                    height={`${h}%`}
                    className="rounded-t-sm"
                  />
                ));
              })()}
            </div>
          )}

          {type === "line" && (
            <div className="relative h-full w-full">
              <Skeleton height="100%" width="100%" className="rounded-md" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-full h-0.5 bg-linear-to-r from-transparent via-muted-foreground/20 to-transparent transform -rotate-12" />
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
              <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-linear-to-t from-muted/50 to-transparent rounded-b-md" />
            </div>
          )}
        </div>

        {/* Chart legend */}
        <div className="flex flex-wrap gap-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={`chart-legend-${index}`} className="flex items-center space-x-2">
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
