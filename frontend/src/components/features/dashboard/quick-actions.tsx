"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  Calendar,
  Compass,
  MapPin,
  MessageCircle,
  Plane,
  Plus,
  Search,
  Settings,
} from "lucide-react";
import Link from "next/link";

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  variant?: "default" | "secondary" | "outline";
  className?: string;
  badge?: string;
}

interface QuickActionsProps {
  layout?: "grid" | "list";
  showDescription?: boolean;
  compact?: boolean;
}

const quickActions: QuickAction[] = [
  {
    id: "search-flights",
    title: "Search Flights",
    description: "Find the best flight deals for your next trip",
    icon: <Plane className="h-4 w-4" />,
    href: "/dashboard/search/flights",
    variant: "default",
    className: "bg-blue-50 border-blue-200 hover:bg-blue-100 text-blue-700",
  },
  {
    id: "search-hotels",
    title: "Find Hotels",
    description: "Discover comfortable accommodations worldwide",
    icon: <MapPin className="h-4 w-4" />,
    href: "/dashboard/search/hotels",
    variant: "outline",
    className: "bg-green-50 border-green-200 hover:bg-green-100 text-green-700",
  },
  {
    id: "create-trip",
    title: "Plan New Trip",
    description: "Start planning your next adventure",
    icon: <Plus className="h-4 w-4" />,
    href: "/dashboard/trips/create",
    variant: "secondary",
    className: "bg-purple-50 border-purple-200 hover:bg-purple-100 text-purple-700",
  },
  {
    id: "ai-chat",
    title: "Ask AI Assistant",
    description: "Get personalized travel recommendations",
    icon: <MessageCircle className="h-4 w-4" />,
    href: "/dashboard/chat",
    variant: "outline",
    className: "bg-orange-50 border-orange-200 hover:bg-orange-100 text-orange-700",
    badge: "AI",
  },
  {
    id: "explore-destinations",
    title: "Explore Destinations",
    description: "Discover new places to visit",
    icon: <Compass className="h-4 w-4" />,
    href: "/dashboard/search/destinations",
    variant: "outline",
    className: "bg-indigo-50 border-indigo-200 hover:bg-indigo-100 text-indigo-700",
  },
  {
    id: "my-trips",
    title: "My Trips",
    description: "View and manage your travel plans",
    icon: <Calendar className="h-4 w-4" />,
    href: "/dashboard/trips",
    variant: "outline",
  },
  {
    id: "advanced-search",
    title: "Advanced Search",
    description: "Use filters for specific requirements",
    icon: <Search className="h-4 w-4" />,
    href: "/dashboard/search",
    variant: "outline",
  },
  {
    id: "settings",
    title: "Settings",
    description: "Manage your account and preferences",
    icon: <Settings className="h-4 w-4" />,
    href: "/dashboard/settings",
    variant: "outline",
  },
];

function ActionButton({
  action,
  showDescription = true,
  compact = false,
}: {
  action: QuickAction;
  showDescription?: boolean;
  compact?: boolean;
}) {
  return (
    <Button
      variant={action.variant || "outline"}
      className={cn(
        "h-auto p-4 flex-col gap-2 relative",
        compact ? "p-3" : "p-4",
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
          <p className="text-xs text-muted-foreground text-center leading-tight">
            {action.description}
          </p>
        )}
      </Link>
    </Button>
  );
}

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
        <Button
          key={action.id}
          variant={action.variant || "outline"}
          className={cn(
            "w-full justify-start gap-3 relative",
            compact ? "h-10 px-3" : "h-12 px-4",
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
                <div className="text-xs text-muted-foreground">
                  {action.description}
                </div>
              )}
            </div>
          </Link>
        </Button>
      ))}
    </div>
  );
}

export function QuickActions({
  layout = "grid",
  showDescription = true,
  compact = false,
}: QuickActionsProps) {
  // Show different actions based on layout and space
  const actionsToShow = compact ? quickActions.slice(0, 6) : quickActions;

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

// Compact version for smaller spaces
export function QuickActionsCompact() {
  return <QuickActions layout="grid" showDescription={false} compact={true} />;
}

// List version for sidebar or narrow spaces
export function QuickActionsList() {
  return <QuickActions layout="list" showDescription={true} compact={false} />;
}
