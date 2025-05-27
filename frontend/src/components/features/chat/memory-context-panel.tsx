"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Brain,
  MapPin,
  DollarSign,
  Calendar,
  User,
  TrendingUp,
  Clock,
  Star,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useMemoryContext, useMemoryInsights } from "@/lib/hooks/use-memory";
import type {
  MemoryContextPanelProps,
  Memory,
  UserPreferences,
  MemoryInsight,
} from "@/types/memory";

export default function MemoryContextPanel({
  userId,
  sessionId,
  className,
  onMemorySelect,
}: MemoryContextPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedTab, setSelectedTab] = useState<
    "context" | "insights" | "recent"
  >("context");

  const {
    data: memoryContext,
    isLoading: contextLoading,
    error: contextError,
  } = useMemoryContext(userId, !!userId);

  const {
    data: insights,
    isLoading: insightsLoading,
    error: insightsError,
  } = useMemoryInsights(userId, !!userId);

  const formatCurrency = (amount: number, currency = "USD") => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).format(amount);
  };

  const renderPreferences = (preferences: UserPreferences) => (
    <div className="space-y-3">
      {preferences.destinations && preferences.destinations.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="h-4 w-4 text-blue-500" />
            <span className="text-sm font-medium">Preferred Destinations</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {preferences.destinations.slice(0, 5).map((dest, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs">
                {dest}
              </Badge>
            ))}
            {preferences.destinations.length > 5 && (
              <Badge variant="outline" className="text-xs">
                +{preferences.destinations.length - 5} more
              </Badge>
            )}
          </div>
        </div>
      )}

      {preferences.budget_range && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="h-4 w-4 text-green-500" />
            <span className="text-sm font-medium">Budget Range</span>
          </div>
          <div className="text-sm text-muted-foreground">
            {formatCurrency(preferences.budget_range.min)} -{" "}
            {formatCurrency(preferences.budget_range.max)}
          </div>
        </div>
      )}

      {preferences.travel_style && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <User className="h-4 w-4 text-purple-500" />
            <span className="text-sm font-medium">Travel Style</span>
          </div>
          <Badge variant="outline" className="text-xs">
            {preferences.travel_style}
          </Badge>
        </div>
      )}

      {preferences.activities && preferences.activities.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Star className="h-4 w-4 text-yellow-500" />
            <span className="text-sm font-medium">Favorite Activities</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {preferences.activities.slice(0, 3).map((activity, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs">
                {activity}
              </Badge>
            ))}
            {preferences.activities.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{preferences.activities.length - 3} more
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  );

  const renderRecentMemories = (memories: Memory[]) => (
    <div className="space-y-2">
      {memories.slice(0, 5).map((memory) => (
        <div
          key={memory.id}
          className="p-2 rounded-lg border bg-card cursor-pointer hover:bg-accent transition-colors"
          onClick={() => onMemorySelect?.(memory)}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm truncate">{memory.content}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="text-xs">
                  {memory.type}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  <Clock className="h-3 w-3 inline mr-1" />
                  {new Date(memory.createdAt).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  const renderInsights = () => {
    if (!insights?.insights) return null;

    const {
      travelPersonality,
      budgetPatterns,
      destinationPreferences,
      recommendations,
    } = insights.insights;

    return (
      <div className="space-y-4">
        {travelPersonality && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <User className="h-4 w-4 text-blue-500" />
              <span className="text-sm font-medium">Travel Personality</span>
            </div>
            <div className="p-3 rounded-lg bg-muted">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">
                  {travelPersonality.type}
                </span>
                <Badge variant="secondary" className="text-xs">
                  {Math.round(travelPersonality.confidence * 100)}% confident
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mb-2">
                {travelPersonality.description}
              </p>
              <div className="flex flex-wrap gap-1">
                {travelPersonality.keyTraits?.slice(0, 3).map((trait, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {trait}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        )}

        {budgetPatterns?.averageSpending && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">Budget Insights</span>
            </div>
            <div className="space-y-2">
              {Object.entries(budgetPatterns.averageSpending)
                .slice(0, 3)
                .map(([category, amount]) => (
                  <div
                    key={category}
                    className="flex justify-between items-center text-sm"
                  >
                    <span className="capitalize">{category}</span>
                    <span className="font-medium">
                      {formatCurrency(amount as number)}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {recommendations && recommendations.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Star className="h-4 w-4 text-yellow-500" />
              <span className="text-sm font-medium">Smart Recommendations</span>
            </div>
            <div className="space-y-2">
              {recommendations.slice(0, 3).map((rec, idx) => (
                <div key={idx} className="p-2 rounded-lg bg-muted">
                  <div className="flex items-center justify-between mb-1">
                    <Badge variant="outline" className="text-xs capitalize">
                      {rec.type}
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      {Math.round(rec.confidence * 100)}%
                    </Badge>
                  </div>
                  <p className="text-xs font-medium">{rec.recommendation}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {rec.reasoning}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  if (contextLoading || insightsLoading) {
    return (
      <Card className={cn("w-80", className)}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="h-4 w-4" />
              Memory Context
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="h-4 bg-muted rounded animate-pulse" />
            <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
            <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (contextError || insightsError) {
    return (
      <Card className={cn("w-80", className)}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4" />
            Memory Context
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Unable to load memory context
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!memoryContext?.context) {
    return (
      <Card className={cn("w-80", className)}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4" />
            Memory Context
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No memory context available
          </p>
        </CardContent>
      </Card>
    );
  }

  const { context } = memoryContext;

  return (
    <Card className={cn("w-80", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4" />
            Memory Context
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-1 mt-3">
          {[
            { id: "context", label: "Profile", icon: User },
            { id: "insights", label: "Insights", icon: TrendingUp },
            { id: "recent", label: "Recent", icon: Clock },
          ].map(({ id, label, icon: Icon }) => (
            <Button
              key={id}
              variant={selectedTab === id ? "secondary" : "ghost"}
              size="sm"
              className="text-xs px-2 py-1 h-7"
              onClick={() => setSelectedTab(id as any)}
            >
              <Icon className="h-3 w-3 mr-1" />
              {label}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        <ScrollArea
          className={cn(
            "transition-all duration-300",
            isExpanded ? "h-96" : "h-48"
          )}
        >
          {selectedTab === "context" &&
            renderPreferences(context.userPreferences)}
          {selectedTab === "insights" && renderInsights()}
          {selectedTab === "recent" &&
            renderRecentMemories(context.recentMemories)}
        </ScrollArea>

        {memoryContext.metadata && (
          <div className="mt-4 pt-3 border-t">
            <div className="text-xs text-muted-foreground space-y-1">
              <div className="flex justify-between">
                <span>Total Memories:</span>
                <span>{memoryContext.metadata.totalMemories}</span>
              </div>
              <div className="flex justify-between">
                <span>Last Updated:</span>
                <span>
                  {new Date(
                    memoryContext.metadata.lastUpdated
                  ).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
