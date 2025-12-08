/**
 * @fileoverview QuickActions component providing grid/list/compact layouts for
 * common travel planning tasks with icons, descriptions, and navigation links.
 */

"use client";

import {
  CalendarIcon,
  CompassIcon,
  MapPinIcon,
  MessageCircleIcon,
  PlaneIcon,
  PlusIcon,
  SearchIcon,
  SettingsIcon,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { type ActionVariant, statusVariants } from "@/lib/variants/status";

/**
 * Gets the tone class for an action variant, if provided.
 *
 * @param actionVariant - Optional action variant for status colors.
 * @returns The status variant class string or undefined.
 */
function GetActionToneClass(actionVariant?: ActionVariant): string | undefined {
  return actionVariant
    ? statusVariants({ action: actionVariant, excludeRing: true })
    : undefined;
}

/**
 * Interface defining a quick action item with metadata for display and navigation.
 */
interface QuickAction {
  /** Unique identifier for the action. */
  id: string;
  /** Display title of the action. */
  title: string;
  /** Descriptive text explaining the action. */
  description: string;
  /** React icon component to display. */
  icon: React.ReactNode;
  /** Navigation URL for the action. */
  href: string;
  /** Button variant styling. */
  variant?: "default" | "secondary" | "outline";
  /** Additional CSS classes for styling. */
  className?: string;
  /** Optional badge text (e.g., "AI"). */
  badge?: string;
  /** Action variant for status colors. */
  actionVariant?: ActionVariant;
}

/**
 * Props interface for the QuickActions component.
 */
interface QuickActionsProps {
  /** Layout style: "grid" or "list". */
  layout?: "grid" | "list";
  /** Whether to show action descriptions. */
  showDescription?: boolean;
  /** Whether to use compact mode with fewer actions. */
  compact?: boolean;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    actionVariant: "search",
    description: "Find the best flight deals for your next trip",
    href: "/dashboard/search/flights",
    icon: <PlaneIcon className="h-4 w-4" />,
    id: "search-flights",
    title: "Search Flights",
    variant: "default",
  },
  {
    actionVariant: "search",
    description: "Discover comfortable accommodations worldwide",
    href: "/dashboard/search/hotels",
    icon: <MapPinIcon className="h-4 w-4" />,
    id: "search-hotels",
    title: "Find Hotels",
    variant: "outline",
  },
  {
    actionVariant: "create",
    description: "Start planning your next adventure",
    href: "/dashboard/trips/create",
    icon: <PlusIcon className="h-4 w-4" />,
    id: "create-trip",
    title: "Plan New Trip",
    variant: "secondary",
  },
  {
    actionVariant: "deals",
    badge: "AI",
    description: "Get personalized travel recommendations",
    href: "/chat",
    icon: <MessageCircleIcon className="h-4 w-4" />,
    id: "ai-chat",
    title: "Ask AI Assistant",
    variant: "outline",
  },
  {
    actionVariant: "explore",
    description: "Discover new places to visit",
    href: "/dashboard/search/destinations",
    icon: <CompassIcon className="h-4 w-4" />,
    id: "explore-destinations",
    title: "Explore Destinations",
    variant: "outline",
  },
  {
    description: "View and manage your travel plans",
    href: "/dashboard/trips",
    icon: <CalendarIcon className="h-4 w-4" />,
    id: "my-trips",
    title: "My Trips",
    variant: "outline",
  },
  {
    description: "Use filters for specific requirements",
    href: "/dashboard/search",
    icon: <SearchIcon className="h-4 w-4" />,
    id: "advanced-search",
    title: "Detailed Search",
    variant: "outline",
  },
  {
    description: "Manage your account and preferences",
    href: "/dashboard/settings",
    icon: <SettingsIcon className="h-4 w-4" />,
    id: "settings",
    title: "Settings",
    variant: "outline",
  },
];

/**
 * Renders a single action button with icon, title, description, and navigation.
 *
 * @param action - The quick action data to render.
 * @param showDescription - Whether to display the action description.
 * @param compact - Whether to use compact styling.
 * @returns The action button component.
 */
function ActionButton({
  action,
  showDescription = true,
  compact = false,
}: {
  action: QuickAction;
  showDescription?: boolean;
  compact?: boolean;
}) {
  const actionToneClass = GetActionToneClass(action.actionVariant);

  return (
    <Button
      variant={action.variant || "outline"}
      className={cn(
        "h-auto flex-col gap-2 relative border-2",
        compact ? "p-3" : "p-4",
        actionToneClass,
        action.className
      )}
      asChild
    >
      <Link href={action.href}>
        {action.badge && (
          <div className="absolute -top-1 -right-1 bg-primary text-primary-foreground text-xs px-1.5 py-0.5 rounded-full">
            {action.badge}
          </div>
        )}
        <div className="flex items-center gap-2 w-full">
          {action.icon}
          <span className={cn("font-medium", compact ? "text-sm" : "text-base")}>
            {action.title}
          </span>
        </div>
        {showDescription && !compact && (
          <p className="text-xs opacity-80 text-center leading-tight">
            {action.description}
          </p>
        )}
      </Link>
    </Button>
  );
}

/**
 * Renders actions in a responsive grid layout.
 *
 * @param actions - Array of quick actions to display.
 * @param showDescription - Whether to show action descriptions.
 * @param compact - Whether to use compact grid sizing.
 * @returns The grid layout component.
 */
function GridLayout({
  actions,
  showDescription,
  compact,
}: {
  actions: QuickAction[];
  showDescription?: boolean;
  compact?: boolean;
}) {
  return (
    <div
      className={cn(
        "grid gap-3",
        compact
          ? "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4"
          : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
      )}
    >
      {actions.map((action) => (
        <ActionButton
          key={action.id}
          action={action}
          showDescription={showDescription}
          compact={compact}
        />
      ))}
    </div>
  );
}

/**
 * Renders actions in a vertical list layout.
 *
 * @param actions - Array of quick actions to display.
 * @param showDescription - Whether to show action descriptions.
 * @param compact - Whether to use compact list sizing.
 * @returns The list layout component.
 */
function ListLayout({
  actions,
  showDescription,
  compact,
}: {
  actions: QuickAction[];
  showDescription?: boolean;
  compact?: boolean;
}) {
  return (
    <div className="space-y-2">
      {actions.map((action) => (
        <ListActionButton
          key={action.id}
          action={action}
          showDescription={showDescription}
          compact={compact}
        />
      ))}
    </div>
  );
}

function ListActionButton({
  action,
  showDescription,
  compact,
}: {
  action: QuickAction;
  showDescription?: boolean;
  compact?: boolean;
}) {
  const actionToneClass = GetActionToneClass(action.actionVariant);

  return (
    <Button
      variant={action.variant || "outline"}
      className={cn(
        "w-full justify-start gap-3 relative border-2",
        compact ? "h-10 px-3" : "h-12 px-4",
        actionToneClass,
        action.className
      )}
      asChild
    >
      <Link href={action.href}>
        {action.badge && (
          <div className="absolute top-1 right-1 bg-primary text-primary-foreground text-xs px-1.5 py-0.5 rounded-full">
            {action.badge}
          </div>
        )}
        {action.icon}
        <div className="flex-1 text-left">
          <div className={cn("font-medium", compact ? "text-sm" : "text-base")}>
            {action.title}
          </div>
          {showDescription && !compact && (
            <div className="text-xs opacity-80">{action.description}</div>
          )}
        </div>
      </Link>
    </Button>
  );
}

/**
 * Main QuickActions component providing common travel planning shortcuts.
 *
 * Supports grid/list layouts and compact mode for different screen sizes.
 * Renders action buttons with icons, titles, descriptions, and navigation links.
 *
 * @param layout - Layout style ("grid" or "list").
 * @param showDescription - Whether to display action descriptions.
 * @param compact - Whether to use compact mode with fewer actions.
 * @returns The QuickActions component.
 */
export function QuickActions({
  layout = "grid",
  showDescription = true,
  compact = false,
}: QuickActionsProps) {
  // Show different actions based on layout and space
  const actionsToShow = compact ? QUICK_ACTIONS.slice(0, 6) : QUICK_ACTIONS;

  return (
    <Card>
      <CardHeader className={compact ? "pb-3" : undefined}>
        <CardTitle className={compact ? "text-lg" : undefined}>Quick Actions</CardTitle>
        {!compact && (
          <CardDescription>
            Common tasks and shortcuts to help you get started
          </CardDescription>
        )}
      </CardHeader>
      <CardContent>
        {layout === "grid" ? (
          <GridLayout
            actions={actionsToShow}
            showDescription={showDescription}
            compact={compact}
          />
        ) : (
          <ListLayout
            actions={actionsToShow}
            showDescription={showDescription}
            compact={compact}
          />
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Compact version of QuickActions for smaller spaces.
 *
 * Shows fewer actions in grid layout without descriptions.
 *
 * @returns The compact QuickActions component.
 */
export function QuickActionsCompact() {
  return <QuickActions layout="grid" showDescription={false} compact={true} />;
}

/**
 * List version of QuickActions for sidebar or narrow spaces.
 *
 * Shows all actions in vertical list layout with descriptions.
 *
 * @returns The list QuickActions component.
 */
export function QuickActionsList() {
  return <QuickActions layout="list" showDescription={true} compact={false} />;
}
