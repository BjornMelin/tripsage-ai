"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  useMemoryInsights,
  useMemoryStats,
  useUpdatePreferences,
} from "@/hooks/use-memory";
import { cn } from "@/lib/utils";
import type { PersonalizationInsightsProps, UserPreferences } from "@/types/memory";
import {
  BarChart3,
  Brain,
  DollarSign,
  Info,
  Lightbulb,
  MapPin,
  RefreshCw,
  Settings,
  Star,
  Target,
  TrendingDown,
  TrendingUp,
  User,
} from "lucide-react";
import { useState } from "react";

export function PersonalizationInsights({
  userId,
  className,
  showRecommendations = true,
  onPreferenceUpdate,
}: PersonalizationInsightsProps) {
  const [_isUpdating, setIsUpdating] = useState(false);
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

  const updatePreferences = useUpdatePreferences(userId);

  const formatCurrency = (amount: number, currency = "USD") => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).format(amount);
  };

  const getTrendIcon = (trend: "increasing" | "decreasing" | "stable") => {
    switch (trend) {
      case "increasing":
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case "decreasing":
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      default:
        return <BarChart3 className="h-4 w-4 text-gray-500" />;
    }
  };

  const _handlePreferenceUpdate = async (preferences: Partial<UserPreferences>) => {
    setIsUpdating(true);
    try {
      await updatePreferences.mutateAsync({
        preferences,
        merge_strategy: "merge",
      });
      onPreferenceUpdate?.(preferences);
      await refetchInsights();
    } catch (error) {
      console.error("Failed to update preferences:", error);
    } finally {
      setIsUpdating(false);
    }
  };

  const renderOverview = () => {
    if (!insights?.insights) return null;

    const { travelPersonality, budgetPatterns, destinationPreferences } =
      insights.insights;

    return (
      <div className="space-y-6">
        {/* Travel Personality */}
        {travelPersonality && (
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <User className="h-5 w-5 text-blue-500" />
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
                    {travelPersonality.keyTraits?.map((trait, idx) => (
                      <Badge key={idx} variant="secondary">
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
              <BarChart3 className="h-5 w-5 text-green-500" />
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
              <MapPin className="h-5 w-5 text-red-500" />
              Favorite Destinations
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {destinationPreferences.topDestinations.slice(0, 4).map((dest, idx) => (
                <Card key={idx}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium">{dest.destination}</h4>
                      <Badge variant="outline">{dest.visits} visits</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Last visit: {new Date(dest.lastVisit).toLocaleDateString()}
                    </div>
                    {dest.satisfaction_score && (
                      <div className="flex items-center gap-2 mt-2">
                        <Star className="h-4 w-4 text-yellow-500" />
                        <span className="text-sm">
                          {dest.satisfaction_score.toFixed(1)}/5
                        </span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderBudgetInsights = () => {
    if (!insights?.insights?.budgetPatterns) return null;

    const { budgetPatterns } = insights.insights;

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-green-500" />
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
                {budgetPatterns.spendingTrends.map((trend, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted"
                  >
                    <div className="flex items-center gap-3">
                      {getTrendIcon(trend.trend)}
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
                            ? "text-red-500"
                            : trend.trend === "decreasing"
                              ? "text-green-500"
                              : "text-gray-500"
                        )}
                      >
                        {trend.percentage_change > 0 ? "+" : ""}
                        {trend.percentage_change}%
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
          <Lightbulb className="h-5 w-5 text-yellow-500" />
          Personalized Recommendations
        </h3>

        <div className="grid gap-4">
          {recommendations.map((rec, idx) => (
            <Card key={idx} className="hover:shadow-md transition-shadow">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-blue-500" />
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
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
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
          <Info className="h-4 w-4" />
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
            <Brain className="h-6 w-6 text-purple-500" />
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
            <RefreshCw
              className={cn("h-4 w-4 mr-2", insightsLoading && "animate-spin")}
            />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4 mr-2" />
            Preferences
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-1 p-1 bg-muted rounded-lg">
        {[
          { id: "overview", label: "Overview", icon: BarChart3 },
          { id: "budget", label: "Budget", icon: DollarSign },
          { id: "destinations", label: "Destinations", icon: MapPin },
          { id: "recommendations", label: "Recommendations", icon: Lightbulb },
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
                Analysis based on {insights.metadata.data_coverage_months} months of
                data
              </span>
              <span>
                Confidence: {Math.round(insights.metadata.confidence_level * 100)}%
              </span>
              <span>
                Updated:{" "}
                {new Date(insights.metadata.analysis_date).toLocaleDateString()}
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
