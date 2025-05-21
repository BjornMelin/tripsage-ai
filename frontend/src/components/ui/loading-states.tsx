"use client"

import React from "react"
import { Skeleton, SkeletonText, SkeletonCard, SkeletonAvatar, SkeletonTable } from "./enhanced-skeleton"
import { cn } from "@/lib/utils"

// Chat loading states
export function ChatMessageSkeleton({ isUser = false }: { isUser?: boolean }) {
  return (
    <div className={cn("flex gap-3 p-4", isUser ? "flex-row-reverse" : "flex-row")}>
      <SkeletonAvatar size="sm" />
      <div className="flex-1 space-y-2 max-w-md">
        <SkeletonText lines={2} />
      </div>
    </div>
  )
}

export function ChatLoadingSkeleton() {
  return (
    <div className="space-y-4">
      <ChatMessageSkeleton />
      <ChatMessageSkeleton isUser />
      <ChatMessageSkeleton />
      <div className="flex gap-3 p-4">
        <SkeletonAvatar size="sm" />
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-muted rounded-full animate-bounce" />
            <div className="w-2 h-2 bg-muted rounded-full animate-bounce [animation-delay:0.1s]" />
            <div className="w-2 h-2 bg-muted rounded-full animate-bounce [animation-delay:0.2s]" />
          </div>
          <span className="text-sm text-muted-foreground">Thinking...</span>
        </div>
      </div>
    </div>
  )
}

// Search results loading
export function SearchResultsSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border rounded-lg p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
            <Skeleton variant="rectangular" className="h-20 w-20 ml-4 rounded-md" />
          </div>
          <div className="flex items-center space-x-4">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-12" />
          </div>
        </div>
      ))}
    </div>
  )
}

// Form loading states
export function FormLoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-full rounded-md" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-10 w-full rounded-md" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-10 w-full rounded-md" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-10 w-full rounded-md" />
        </div>
      </div>
      <Skeleton className="h-10 w-32 rounded-md" />
    </div>
  )
}

// Profile loading state
export function ProfileLoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <SkeletonAvatar size="lg" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="text-center space-y-2">
            <Skeleton className="h-8 w-12 mx-auto" />
            <Skeleton className="h-4 w-16 mx-auto" />
          </div>
        ))}
      </div>

      {/* Content */}
      <div className="space-y-4">
        <Skeleton className="h-5 w-32" />
        <SkeletonText lines={4} />
      </div>
    </div>
  )
}

// Settings page loading
export function SettingsLoadingSkeleton() {
  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="space-y-2">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-64" />
      </div>

      {/* Settings sections */}
      {Array.from({ length: 3 }).map((_, sectionIndex) => (
        <div key={sectionIndex} className="space-y-4">
          <Skeleton className="h-6 w-48" />
          <div className="border rounded-lg p-6 space-y-6">
            {Array.from({ length: 3 }).map((_, itemIndex) => (
              <div key={itemIndex} className="flex items-center justify-between">
                <div className="space-y-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-48" />
                </div>
                <Skeleton className="h-6 w-12 rounded-full" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// Analytics/Dashboard cards
export function AnalyticsCardSkeleton() {
  return (
    <div className="border rounded-lg p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-28" />
        <Skeleton variant="circular" className="h-4 w-4" />
      </div>
      <Skeleton className="h-8 w-20" />
      <div className="flex items-center space-x-2">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-6" />
      </div>
    </div>
  )
}

export function AnalyticsDashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <AnalyticsCardSkeleton key={i} />
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border rounded-lg p-6 space-y-4">
          <Skeleton className="h-5 w-32" />
          <Skeleton variant="rectangular" className="h-64 w-full rounded-md" />
        </div>
        <div className="border rounded-lg p-6 space-y-4">
          <Skeleton className="h-5 w-28" />
          <Skeleton variant="rectangular" className="h-64 w-full rounded-md" />
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-lg p-6 space-y-4">
        <Skeleton className="h-5 w-36" />
        <SkeletonTable rows={8} columns={5} />
      </div>
    </div>
  )
}

// Navigation loading
export function NavigationSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center space-x-3 px-2 py-2">
          <Skeleton variant="circular" className="h-4 w-4" />
          <Skeleton className="h-4 w-24" />
        </div>
      ))}
    </div>
  )
}

// Inline loading spinner for buttons and small areas
export function InlineSpinner({ size = "sm", className }: { size?: "sm" | "md" | "lg"; className?: string }) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  }

  return (
    <div
      className={cn(
        "animate-spin rounded-full border-2 border-current border-t-transparent",
        sizeClasses[size],
        className
      )}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  )
}

// Full page loading overlay
export function PageLoadingOverlay({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="text-center space-y-4">
        <InlineSpinner size="lg" />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  )
}