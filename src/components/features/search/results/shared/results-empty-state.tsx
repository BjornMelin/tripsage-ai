/**
 * @fileoverview Empty state component for search results.
 *
 * Displays a consistent "no results found" UI across flight, hotel,
 * and activity search result views.
 */

"use client";

import type { LucideIcon } from "lucide-react";
import { RefreshCwIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

/** Props for the ResultsEmptyState component. */
export interface ResultsEmptyStateProps {
  /** Icon to display above the message. */
  icon: LucideIcon;
  /** Main heading text. */
  title: string;
  /** Description text below the heading. */
  description: string;
  /** Label for the action button. */
  actionLabel?: string;
  /** Callback when action button is clicked. */
  onAction?: () => void;
}

/**
 * Empty state component for search results.
 *
 * Provides a consistent UI when no results are found, with customizable
 * icon, messaging, and action button.
 *
 * @example
 * ```tsx
 * <ResultsEmptyState
 *   icon={PlaneIcon}
 *   title="No flights found"
 *   description="Try adjusting your search dates or filters"
 *   actionLabel="Modify Search"
 *   onAction={handleModifySearch}
 * />
 * ```
 */
export function ResultsEmptyState({
  icon: Icon,
  title,
  description,
  actionLabel = "Modify Search",
  onAction,
}: ResultsEmptyStateProps) {
  return (
    <Card className="p-12 text-center">
      <Icon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground mb-4">{description}</p>
      <Button
        variant="outline"
        onClick={onAction}
        disabled={!onAction}
        aria-label={onAction ? actionLabel : `${actionLabel} unavailable`}
        aria-disabled={!onAction}
        title={onAction ? undefined : `${actionLabel} unavailable`}
      >
        <RefreshCwIcon className="h-4 w-4 mr-2" />
        {actionLabel}
      </Button>
    </Card>
  );
}
