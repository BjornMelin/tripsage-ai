import * as React from "react";
import { Skeleton } from "./skeleton";
import {
  CardSkeleton,
  ListItemSkeleton,
  AvatarSkeleton,
  FormSkeleton,
} from "./loading-skeletons";
import { cn } from "@/lib/utils";

/**
 * Flight search result skeleton
 */
export interface FlightSkeletonProps {
  className?: string;
}

export const FlightSkeleton = React.forwardRef<
  HTMLDivElement,
  FlightSkeletonProps
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("rounded-lg border p-4 space-y-4", className)}
      role="status"
      aria-label="Loading flight results"
      {...props}
    >
      {/* Flight route and times */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {/* Departure */}
          <div className="text-center space-y-1">
            <Skeleton height="1.5rem" width="80px" />
            <Skeleton height="1rem" width="60px" />
          </div>

          {/* Flight path */}
          <div className="flex items-center space-x-2">
            <Skeleton height="0.5rem" width="60px" />
            <Skeleton height="1rem" width="20px" variant="rounded" />
            <Skeleton height="0.5rem" width="60px" />
          </div>

          {/* Arrival */}
          <div className="text-center space-y-1">
            <Skeleton height="1.5rem" width="80px" />
            <Skeleton height="1rem" width="60px" />
          </div>
        </div>

        {/* Price */}
        <div className="text-right space-y-1">
          <Skeleton height="1.5rem" width="100px" />
          <Skeleton height="1rem" width="80px" />
        </div>
      </div>

      {/* Flight details */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center space-x-4">
          <Skeleton height="1rem" width="100px" />
          <Skeleton height="1rem" width="80px" />
          <Skeleton height="1rem" width="60px" />
        </div>
        <Skeleton height="2rem" width="100px" className="rounded-md" />
      </div>
    </div>
  );
});

FlightSkeleton.displayName = "FlightSkeleton";

/**
 * Hotel/accommodation search result skeleton
 */
export interface HotelSkeletonProps {
  className?: string;
}

export const HotelSkeleton = React.forwardRef<
  HTMLDivElement,
  HotelSkeletonProps
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("overflow-hidden", className)}
      role="status"
      aria-label="Loading hotel results"
      {...props}
    >
      <CardSkeleton
        hasImage
        titleLines={1}
        bodyLines={0}
        className="border-none p-0"
      />

      <div className="p-4 space-y-3">
        {/* Hotel rating */}
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} height="1rem" width="1rem" />
            ))}
          </div>
          <Skeleton height="1rem" width="60px" />
        </div>

        {/* Location */}
        <Skeleton height="1rem" width="70%" />

        {/* Amenities */}
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton
              key={index}
              height="1.5rem"
              width="80px"
              className="rounded-full"
            />
          ))}
        </div>

        {/* Price and booking */}
        <div className="flex items-end justify-between pt-2">
          <div className="space-y-1">
            <Skeleton height="1rem" width="100px" />
            <Skeleton height="1.5rem" width="120px" />
          </div>
          <Skeleton height="2.5rem" width="100px" className="rounded-md" />
        </div>
      </div>
    </div>
  );
});

HotelSkeleton.displayName = "HotelSkeleton";

/**
 * Trip card skeleton
 */
export interface TripSkeletonProps {
  className?: string;
}

export const TripSkeleton = React.forwardRef<HTMLDivElement, TripSkeletonProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("overflow-hidden", className)}
        role="status"
        aria-label="Loading trip information"
        {...props}
      >
        <CardSkeleton
          hasImage
          titleLines={1}
          bodyLines={0}
          className="border-none p-0"
        />

        <div className="p-4 space-y-3">
          {/* Trip dates */}
          <div className="flex items-center space-x-2">
            <Skeleton height="1rem" width="16px" />
            <Skeleton height="1rem" width="140px" />
          </div>

          {/* Trip destination */}
          <div className="flex items-center space-x-2">
            <Skeleton height="1rem" width="16px" />
            <Skeleton height="1rem" width="120px" />
          </div>

          {/* Trip status and budget */}
          <div className="flex items-center justify-between pt-2">
            <Skeleton height="1.5rem" width="80px" className="rounded-full" />
            <Skeleton height="1.25rem" width="100px" />
          </div>
        </div>
      </div>
    );
  }
);

TripSkeleton.displayName = "TripSkeleton";

/**
 * Destination card skeleton
 */
export interface DestinationSkeletonProps {
  className?: string;
}

export const DestinationSkeleton = React.forwardRef<
  HTMLDivElement,
  DestinationSkeletonProps
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("overflow-hidden", className)}
      role="status"
      aria-label="Loading destination information"
      {...props}
    >
      {/* Destination image with overlay */}
      <div className="relative">
        <CardSkeleton
          hasImage
          titleLines={0}
          bodyLines={0}
          className="border-none p-0"
        />
        <div className="absolute top-4 right-4">
          <Skeleton height="2rem" width="2rem" variant="rounded" />
        </div>
      </div>

      <div className="p-4 space-y-3">
        {/* Destination name and description */}
        <Skeleton height="1.5rem" width="70%" />
        <Skeleton lines={2} height="1rem" />

        {/* Weather and best time */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Skeleton height="1rem" width="16px" />
            <Skeleton height="1rem" width="80px" />
          </div>
          <Skeleton height="1rem" width="100px" />
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton
              key={index}
              height="1.5rem"
              width="60px"
              className="rounded-full"
            />
          ))}
        </div>
      </div>
    </div>
  );
});

DestinationSkeleton.displayName = "DestinationSkeleton";

/**
 * Itinerary item skeleton
 */
export interface ItineraryItemSkeletonProps {
  className?: string;
}

export const ItineraryItemSkeleton = React.forwardRef<
  HTMLDivElement,
  ItineraryItemSkeletonProps
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("flex space-x-4 p-4 border rounded-lg", className)}
      role="status"
      aria-label="Loading itinerary item"
      {...props}
    >
      {/* Time indicator */}
      <div className="flex flex-col items-center">
        <Skeleton height="2rem" width="2rem" variant="rounded" />
        <Skeleton height="30px" width="2px" className="mt-2" />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2">
        <div className="flex items-center justify-between">
          <Skeleton height="1.25rem" width="60%" />
          <Skeleton height="1rem" width="80px" />
        </div>
        <Skeleton lines={2} height="1rem" />
        <div className="flex items-center space-x-4">
          <Skeleton height="1rem" width="100px" />
          <Skeleton height="1rem" width="80px" />
        </div>
      </div>
    </div>
  );
});

ItineraryItemSkeleton.displayName = "ItineraryItemSkeleton";

/**
 * Chat message skeleton
 */
export interface ChatMessageSkeletonProps {
  isUser?: boolean;
  className?: string;
}

export const ChatMessageSkeleton = React.forwardRef<
  HTMLDivElement,
  ChatMessageSkeletonProps
>(({ isUser = false, className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "flex space-x-3 p-4",
        isUser ? "justify-end" : "justify-start",
        className
      )}
      role="status"
      aria-label="Loading chat message"
      {...props}
    >
      {!isUser && <AvatarSkeleton size="sm" />}

      <div className={cn("max-w-md space-y-2", isUser && "order-first")}>
        <Skeleton
          height="1rem"
          width={isUser ? "60%" : "80%"}
          className={cn("rounded-lg", isUser ? "ml-auto" : "mr-auto")}
        />
        <Skeleton
          lines={Math.floor(Math.random() * 3) + 1}
          height="1rem"
          className={cn("rounded-lg", isUser ? "ml-auto" : "mr-auto")}
        />
      </div>

      {isUser && <AvatarSkeleton size="sm" />}
    </div>
  );
});

ChatMessageSkeleton.displayName = "ChatMessageSkeleton";

/**
 * Search filter skeleton
 */
export interface SearchFilterSkeletonProps {
  className?: string;
  sections?: number;
}

export const SearchFilterSkeleton = React.forwardRef<
  HTMLDivElement,
  SearchFilterSkeletonProps
>(({ className, sections = 4, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("border rounded-lg", className)}
      role="status"
      aria-label="Loading search filters"
      {...props}
    >
      {/* Use FormSkeleton as base for overall structure */}
      <div className="p-4 space-y-4">
        {Array.from({ length: sections }).map((_, sectionIndex) => (
          <div key={sectionIndex} className="space-y-2">
            {/* Section title */}
            <Skeleton height="1.25rem" width="30%" />

            {/* Section options using ListItemSkeleton pattern */}
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, itemIndex) => (
                <ListItemSkeleton
                  key={itemIndex}
                  hasAvatar={false}
                  hasAction={false}
                  titleLines={1}
                  subtitleLines={0}
                  className="p-0 space-x-2"
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

SearchFilterSkeleton.displayName = "SearchFilterSkeleton";
