/**
 * @fileoverview Personalization insights panel rendering memory summaries.
 */

"use client";

import type { MemoryContextResponse } from "@schemas/chat";
// import type { UserPreferences } from "@schemas/memory"; // Future implementation
import {
  BarChart3Icon,
  BrainIcon,
  CopyIcon,
  DollarSignIcon,
  InfoIcon,
  LightbulbIcon,
  MapPinIcon,
  RefreshCwIcon,
  SettingsIcon,
  StarIcon,
  TargetIcon,
  TrendingDownIcon,
  TrendingUpIcon,
  UserIcon,
} from "lucide-react";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  useMemoryContext,
  useMemoryInsights,
  useMemoryStats,
  // useUpdatePreferences, // Future implementation
} from "@/hooks/use-memory";
import { TREND_COLORS } from "@/lib/variants/status";
export type PersonalizationInsightsProps = {
  userId: string;
  className?: string;
  showRecommendations?: boolean;
  onPreferenceUpdate?: (preferences: unknown) => void;
};

import { cn } from "@/lib/utils";

/**
 * Spending trend colors with inverted semantic:
 * increasing=red (spending more is concerning), decreasing=green (spending less is good)
 * Uses 500 weight to align with TREND_COLORS for consistency across cards.
 */
const SPENDING_TREND_COLORS = {
  decreasing: "text-green-500",
  increasing: "text-red-500",
  stable: "text-gray-500",
} as const;

export function PersonalizationInsights({
  userId,
  className,
  showRecommendations = true,
  onPreferenceUpdate: _onPreferenceUpdate, // Future implementation
}: PersonalizationInsightsProps) {
  // const [isUpdating, setIsUpdating] = useState(false); // Future implementation
  const [selectedView, setSelectedView] = useState<
    "overview" | "budget" | "destinations" | "recommendations"
  >("overview");

  const {
    data: insights,
    isLoading: insightsLoading,
    error: insightsError,
    refetch: refetchInsights,
  } = useMemoryInsights(userId, !!userId);

  const { data: stats, isLoading: statsLoading } = useMemoryStats(userId, !!userId);
  const { data: recentMemories, isLoading: recentMemoriesLoading } = useMemoryContext(
    userId,
    !!userId
  );

  // const updatePreferences = useUpdatePreferences(userId); // Future implementation

  const formatCurrency = (amount: number, currency = "USD") => {
    return new Intl.NumberFormat("en-US", {
      currency,
      style: "currency",
    }).format(amount);
  };

  const formatTimestamp = (iso?: string) => {
    if (!iso) return "Unknown";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "Unknown";
    return new Intl.DateTimeFormat("en", {
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      month: "short",
      year: "numeric",
    }).format(date);
  };

  const truncateId = (id?: string) => {
    if (!id) return "";
    return id.length > 10 ? `${id.slice(0, 8)}…` : id;
  };

  /**
   * Trend colors aligned with statusVariants urgency mapping.
   * For general trends: increasing=green, decreasing=red, stable=neutral
   */
  const renderTrendIcon = (
    trend: "increasing" | "decreasing" | "stable",
    colorMap: typeof TREND_COLORS | typeof SPENDING_TREND_COLORS = TREND_COLORS
  ) => {
    switch (trend) {
      case "increasing":
        return <TrendingUpIcon className={`h-4 w-4 ${colorMap.increasing}`} />;
      case "decreasing":
        return <TrendingDownIcon className={`h-4 w-4 ${colorMap.decreasing}`} />;
      default:
        return <BarChart3Icon className={`h-4 w-4 ${colorMap.stable}`} />;
    }
  };

  // const handlePreferenceUpdate = async (preferences: Partial<UserPreferences>) => { // Future implementation
  //   setIsUpdating(true);
  //   try {
  //     await updatePreferences.mutateAsync({
  //       preferences,
  //       merge_strategy: "merge",
  //     });
  //     onPreferenceUpdate?.(preferences);
  //     await refetchInsights();
  //   } catch (error) {
  //     console.error("Failed to update preferences:", error);
  //   } finally {
  //     setIsUpdating(false);
  //   }
  // };

  const renderOverview = () => {
    if (!insights?.insights) return null;

    const {
      travelPersonality,
      budgetPatterns: _budgetPatterns,
      destinationPreferences,
    } = insights.insights;

    const recent = (recentMemories?.context ?? []) as MemoryContextResponse[];

    return (
      <div className="space-y-6">
        {/* Travel Personality */}
        {travelPersonality && (
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <UserIcon className="h-5 w-5 text-blue-500" />
              Travel Personality
            </h3>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h4 className="font-medium text-lg">{travelPersonality.type}</h4>
                    <p className="text-sm text-muted-foreground">
                      {travelPersonality.description}
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-500">
                      {Math.round(travelPersonality.confidence * 100)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Confidence</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-sm font-medium">Key Traits:</div>
                  <div className="flex flex-wrap gap-2">
                    {travelPersonality.keyTraits?.map((trait) => (
                      <Badge key={trait} variant="secondary">
                        {trait}
                      </Badge>
                    ))}
                  </div>
                </div>

                <Progress value={travelPersonality.confidence * 100} className="mt-4" />
              </CardContent>
            </Card>
          </div>
        )}

        {/* Quick Stats */}
        {stats && (
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <BarChart3Icon className="h-5 w-5 text-green-500" />
              Memory Statistics
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6 text-center">
                  <div className="text-2xl font-bold text-blue-500">
                    {stats.totalMemories}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Memories</div>
                </CardContent>
              </Card>

              {Object.entries(stats.memoryTypes)
                .slice(0, 3)
                .map(([type, count]) => (
                  <Card key={type}>
                    <CardContent className="pt-6 text-center">
                      <div className="text-2xl font-bold text-purple-500">{count}</div>
                      <div className="text-sm text-muted-foreground capitalize">
                        {type}
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>
          </div>
        )}

        {/* Top Destinations */}
        {destinationPreferences?.topDestinations && (
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <MapPinIcon className="h-5 w-5 text-red-500" />
              Favorite Destinations
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {destinationPreferences.topDestinations.slice(0, 4).map((dest) => (
                <Card key={dest.destination}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium">{dest.destination}</h4>
                      <Badge variant="outline">{dest.visits} visits</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Last visit: {new Date(dest.lastVisit).toLocaleDateString()}
                    </div>
                    {dest.satisfactionScore && (
                      <div className="flex items-center gap-2 mt-2">
                        <StarIcon className="h-4 w-4 text-yellow-500" />
                        <span className="text-sm">
                          {dest.satisfactionScore.toFixed(1)}/5
                        </span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <LightbulbIcon className="h-5 w-5 text-amber-500" />
            Recent Memories
          </h3>
          {recentMemoriesLoading ? (
            <p className="text-sm text-muted-foreground">Loading recent memories…</p>
          ) : recent.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent memories yet.</p>
          ) : (
            <div className="grid grid-cols-1 md-grid-cols-2 md:grid-cols-2 gap-4">
              {recent.slice(0, 6).map((mem, idx) => (
                <Card key={mem.id ?? `mem-${idx}`}>
                  <CardContent className="pt-5 space-y-2">
                    <div className="text-sm text-muted-foreground flex items-center justify-between gap-2">
                      <span>{formatTimestamp(mem.createdAt)}</span>
                      {mem.id ? (
                        <div className="flex items-center gap-1">
                          <span
                            className="text-[11px] font-mono text-muted-foreground/80"
                            title={mem.id}
                          >
                            {truncateId(mem.id)}
                          </span>
                          <button
                            aria-label="Copy memory ID"
                            className="text-muted-foreground hover:text-foreground transition"
                            onClick={() =>
                              navigator.clipboard
                                ?.writeText(mem.id ?? "")
                                .catch(() => undefined)
                            }
                            type="button"
                          >
                            <CopyIcon className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : null}
                    </div>
                    <p className="text-sm leading-relaxed">{mem.context}</p>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{mem.source ?? "unknown"}</span>
                      {typeof mem.score === "number" ? (
                        <span className="font-medium">
                          {Math.round(mem.score * 100)}%
                        </span>
                      ) : null}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderBudgetInsights = () => {
    if (!insights?.insights?.budgetPatterns) return null;

    const { budgetPatterns } = insights.insights;

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <DollarSignIcon className="h-5 w-5 text-green-500" />
          Budget Analysis
        </h3>

        {/* Average Spending */}
        {budgetPatterns.averageSpending && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Average Spending by Category</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(budgetPatterns.averageSpending).map(
                  ([category, amount]) => (
                    <div key={category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-blue-500" />
                        <span className="capitalize font-medium">{category}</span>
                      </div>
                      <span className="font-mono">
                        {formatCurrency(amount as number)}
                      </span>
                    </div>
                  )
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Spending Trends */}
        {budgetPatterns.spendingTrends && budgetPatterns.spendingTrends.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Spending Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {budgetPatterns.spendingTrends.map((trend) => (
                  <div
                    key={`${trend.category}-${trend.trend}`}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted"
                  >
                    <div className="flex items-center gap-3">
                      {renderTrendIcon(trend.trend, SPENDING_TREND_COLORS)}
                      <div>
                        <div className="font-medium capitalize">{trend.category}</div>
                        <div className="text-sm text-muted-foreground capitalize">
                          {trend.trend} trend
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div
                        className={cn(
                          "font-mono text-sm",
                          trend.trend === "increasing"
                            ? SPENDING_TREND_COLORS.increasing
                            : trend.trend === "decreasing"
                              ? SPENDING_TREND_COLORS.decreasing
                              : SPENDING_TREND_COLORS.stable
                        )}
                      >
                        {trend.percentageChange > 0 ? "+" : ""}
                        {trend.percentageChange}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  const renderRecommendations = () => {
    if (!insights?.insights?.recommendations) return null;

    const { recommendations } = insights.insights;

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <LightbulbIcon className="h-5 w-5 text-yellow-500" />
          Personalized Recommendations
        </h3>

        <div className="grid gap-4">
          {recommendations.map((rec) => (
            <Card
              key={`${rec.type}-${rec.recommendation}`}
              className="hover:shadow-md transition-shadow"
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <TargetIcon className="h-4 w-4 text-blue-500" />
                    <Badge variant="outline" className="capitalize">
                      {rec.type}
                    </Badge>
                  </div>
                  <Badge variant="secondary">
                    {Math.round(rec.confidence * 100)}% confidence
                  </Badge>
                </div>

                <h4 className="font-medium mb-2">{rec.recommendation}</h4>
                <p className="text-sm text-muted-foreground">{rec.reasoning}</p>

                <div className="mt-4 flex gap-2">
                  <Button size="sm" variant="outline">
                    Learn More
                  </Button>
                  <Button size="sm">Apply Suggestion</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  };

  if (insightsLoading || statsLoading) {
    return (
      <div className={cn("space-y-6", className)}>
        <div className="h-8 bg-muted rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {["skeleton-0", "skeleton-1", "skeleton-2", "skeleton-3"].map((id) => (
            <Card key={id}>
              <CardContent className="pt-6">
                <div className="space-y-2">
                  <div className="h-4 bg-muted rounded animate-pulse" />
                  <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (insightsError) {
    return (
      <div className={cn("space-y-6", className)}>
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            Unable to load personalization insights. Please try refreshing the page.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <BrainIcon className="h-6 w-6 text-purple-500" />
            Personalization Insights
          </h2>
          <p className="text-muted-foreground">
            AI-powered analysis of your travel patterns and preferences
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchInsights()}
            disabled={insightsLoading}
          >
            <RefreshCwIcon
              className={cn("h-4 w-4 mr-2", insightsLoading && "animate-spin")}
            />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <SettingsIcon className="h-4 w-4 mr-2" />
            Preferences
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-1 p-1 bg-muted rounded-lg">
        {[
          { icon: BarChart3Icon, id: "overview", label: "Overview" },
          { icon: DollarSignIcon, id: "budget", label: "Budget" },
          { icon: MapPinIcon, id: "destinations", label: "Destinations" },
          { icon: LightbulbIcon, id: "recommendations", label: "Recommendations" },
        ].map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={selectedView === id ? "secondary" : "ghost"}
            size="sm"
            className="flex-1"
            onClick={() =>
              setSelectedView(
                id as "overview" | "budget" | "destinations" | "recommendations"
              )
            }
          >
            <Icon className="h-4 w-4 mr-2" />
            {label}
          </Button>
        ))}
      </div>

      {/* Content */}
      <div className="h-[600px] overflow-y-auto">
        {selectedView === "overview" && renderOverview()}
        {selectedView === "budget" && renderBudgetInsights()}
        {selectedView === "destinations" && renderOverview()}
        {selectedView === "recommendations" &&
          showRecommendations &&
          renderRecommendations()}
      </div>

      {/* Metadata */}
      {insights?.metadata && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Analysis based on {insights.metadata.dataCoverageMonths} months of data
              </span>
              <span>
                Confidence: {Math.round(insights.metadata.confidenceLevel * 100)}%
              </span>
              <span>
                Updated: {new Date(insights.metadata.analysisDate).toLocaleDateString()}
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
