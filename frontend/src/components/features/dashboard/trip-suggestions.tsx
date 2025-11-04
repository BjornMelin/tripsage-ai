/**
 * @fileoverview TripSuggestions component displaying AI-powered travel recommendations
 * with personalized suggestions based on user memory and preferences, including
 * budget-aware filtering and interactive trip planning features.
 */

"use client";

import { Brain, Clock, MapPin, Sparkles, Star, TrendingUp } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useMemoryContext, useMemoryInsights } from "@/hooks/use-memory";
import { type TripSuggestion, useTripSuggestions } from "@/hooks/use-trips";
import { useBudgetStore } from "@/stores/budget-store";

/**
 * Props interface for the TripSuggestions component.
 */
interface TripSuggestionsProps {
  /** Maximum number of suggestions to display. */
  limit?: number;
  /** Whether to show empty state when no suggestions available. */
  showEmpty?: boolean;
  /** User ID for personalized memory-based suggestions. */
  userId?: string;
  /** Whether to show AI memory-based personalized suggestions. */
  showMemoryBased?: boolean;
}

/**
 * Skeleton loading component for trip suggestion cards.
 *
 * @returns The skeleton loading component.
 */
function SuggestionCardSkeleton() {
  return (
    <div className="p-4 border border-border rounded-lg">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <Skeleton className="h-4 w-48 mb-2" />
          <div className="flex items-center gap-2 mb-2">
            <Skeleton className="h-3 w-3" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
        <Skeleton className="h-5 w-16" />
      </div>
      <Skeleton className="h-3 w-full mb-2" />
      <Skeleton className="h-3 w-3/4 mb-3" />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-3 w-16" />
        </div>
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  );
}

/**
 * Individual trip suggestion card component with detailed trip information.
 *
 * @param suggestion - The trip suggestion data to display.
 * @returns The suggestion card component.
 */
function SuggestionCard({ suggestion }: { suggestion: TripSuggestion }) {
  /**
   * Get emoji icon for trip category.
   *
   * @param category - The trip category.
   * @returns The emoji icon for the category.
   */
  const getCategoryIcon = (category: TripSuggestion["category"]) => {
    switch (category) {
      case "adventure":
        return "🏔️";
      case "relaxation":
        return "🌴";
      case "culture":
        return "🏛️";
      case "nature":
        return "🌿";
      case "city":
        return "🏙️";
      case "beach":
        return "🏖️";
      default:
        return "✈️";
    }
  };

  /**
   * Get CSS class for difficulty level text color.
   *
   * @param difficulty - The trip difficulty level.
   * @returns CSS class for text color.
   */
  const getDifficultyColor = (difficulty?: TripSuggestion["difficulty"]) => {
    switch (difficulty) {
      case "easy":
        return "text-green-600";
      case "moderate":
        return "text-yellow-600";
      case "challenging":
        return "text-red-600";
      default:
        return "text-muted-foreground";
    }
  };

  /**
   * Format price with proper currency formatting.
   *
   * @param price - The numeric price value.
   * @param currency - The currency code (e.g., "USD").
   * @returns Formatted price string.
   */
  const formatPrice = (price: number, currency: string) => {
    return new Intl.NumberFormat("en-US", {
      currency: currency,
      minimumFractionDigits: 0,
      style: "currency",
    }).format(price);
  };

  return (
    <div className="p-4 border border-border rounded-lg hover:bg-accent/50 transition-colors group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="font-medium text-sm group-hover:text-primary transition-colors">
              {suggestion.title}
            </h4>
            {suggestion.trending && (
              <Badge variant="secondary" className="text-xs">
                <Sparkles className="h-3 w-3 mr-1" />
                Trending
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <MapPin className="h-3 w-3" />
            <span>{suggestion.destination}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
            <span>{suggestion.rating}</span>
          </div>
          <div className="text-lg font-semibold text-primary">
            {formatPrice(suggestion.estimated_price, suggestion.currency)}
          </div>
        </div>
      </div>

      <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
        {suggestion.description}
      </p>

      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{suggestion.duration} days</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-sm">{getCategoryIcon(suggestion.category)}</span>
            <span className="capitalize">{suggestion.category}</span>
          </div>
          {suggestion.difficulty && (
            <span className={`capitalize ${getDifficultyColor(suggestion.difficulty)}`}>
              {suggestion.difficulty}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        {suggestion.highlights.slice(0, 3).map((highlight) => (
          <Badge key={highlight} variant="outline" className="text-xs">
            {highlight}
          </Badge>
        ))}
        {suggestion.highlights.length > 3 && (
          <Badge variant="outline" className="text-xs">
            +{suggestion.highlights.length - 3} more
          </Badge>
        )}
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-border">
        <span className="text-xs text-muted-foreground">
          Best time: {suggestion.best_time_to_visit}
        </span>
        <Button size="sm" variant="outline" asChild>
          <Link href={`/dashboard/trips/create?suggestion=${suggestion.id}`}>
            Plan Trip
          </Link>
        </Button>
      </div>
    </div>
  );
}

/**
 * Empty state component shown when no trip suggestions are available.
 *
 * @returns The empty state component.
 */
function EmptyState() {
  return (
    <div className="text-center py-8">
      <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
        <Sparkles className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        Get personalized trip suggestions based on your preferences.
      </p>
      <Button asChild size="sm">
        <Link href="/chat">Chat with AI for Suggestions</Link>
      </Button>
    </div>
  );
}

/**
 * Main TripSuggestions component displaying AI-powered travel recommendations.
 *
 * Combines API-based suggestions with personalized memory-based recommendations,
 * supports budget filtering, loading states, and interactive trip planning.
 *
 * @param limit - Maximum number of suggestions to display.
 * @param showEmpty - Whether to show empty state when no suggestions available.
 * @param userId - User ID for personalized memory-based suggestions.
 * @param showMemoryBased - Whether to show AI memory-based personalized suggestions.
 * @returns The TripSuggestions component.
 */
export function TripSuggestions({
  limit = 4,
  showEmpty = true,
  userId,
  showMemoryBased = true,
}: TripSuggestionsProps) {
  const { activeBudget } = useBudgetStore();

  // Use React Query hook to fetch trip suggestions
  const { data: apiSuggestions, isLoading } = useTripSuggestions({
    budget_max: activeBudget?.totalAmount,
    limit: limit + 2, // Get extra in case we filter some out
  });

  // Memory-based recommendations
  const { data: memoryContext, isLoading: _memoryLoading } = useMemoryContext(
    userId || "",
    !!userId && showMemoryBased
  );

  const { data: insights, isLoading: _insightsLoading } = useMemoryInsights(
    userId || "",
    !!userId && showMemoryBased
  );

  /**
   * Generate personalized trip suggestions based on user memory and preferences.
   *
   * @returns Array of memory-based trip suggestions.
   */
  const generateMemoryBasedSuggestions = (): TripSuggestion[] => {
    if (!memoryContext?.context || !insights?.insights) return [];

    const { userPreferences, travelPatterns: _travelPatterns } = memoryContext.context;
    const {
      recommendations,
      budgetPatterns,
      travelPersonality: _travelPersonality,
    } = insights.insights;

    const memoryBasedSuggestions: TripSuggestion[] = [];

    // Add suggestions based on user preferences
    if (userPreferences.destinations) {
      userPreferences.destinations.slice(0, 2).forEach((dest, idx) => {
        memoryBasedSuggestions.push({
          best_time_to_visit: "Year-round",
          category: userPreferences.travelStyle === "luxury" ? "relaxation" : "culture",
          currency: "USD",
          description: `Based on your previous love for ${dest}, here's a personalized return trip.`,
          destination: dest,
          duration: 7,
          estimated_price: budgetPatterns?.averageSpending?.accommodation || 2000,
          highlights: userPreferences.activities?.slice(0, 3) || ["Sightseeing"],
          id: `memory-dest-${idx}`,
          rating: 4.7,
          title: `Return to ${dest}`,
          trending: true,
        });
      });
    }

    // Add suggestions based on AI recommendations
    if (recommendations) {
      recommendations.slice(0, 2).forEach((rec, idx) => {
        if (rec.type === "destination") {
          memoryBasedSuggestions.push({
            best_time_to_visit: "Spring/Fall",
            category: "adventure",
            currency: "USD",
            description: rec.reasoning,
            destination: rec.recommendation.split(" ")[0] || "Somewhere Amazing",
            duration: 5,
            estimated_price: budgetPatterns?.averageSpending?.total || 2500,
            highlights: ["AI Recommended", "Personalized"],
            id: `memory-ai-${idx}`,
            rating: 4.6,
            title: rec.recommendation,
            trending: true,
          });
        }
      });
    }

    return memoryBasedSuggestions.slice(0, 2);
  };

  const memoryBasedSuggestions = generateMemoryBasedSuggestions();

  // Combine memory-based and API suggestions
  const allSuggestions = [...memoryBasedSuggestions, ...(apiSuggestions || [])];

  // Limit the number of suggestions
  const filteredSuggestions = allSuggestions.slice(0, limit);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trip Suggestions</CardTitle>
          <CardDescription>AI-powered travel recommendations</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {["skeleton-0", "skeleton-1"].map((id) => (
            <SuggestionCardSkeleton key={id} />
          ))}
        </CardContent>
        <CardFooter>
          <Skeleton className="h-9 w-full" />
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {showMemoryBased && memoryBasedSuggestions.length > 0 && (
            <Brain className="h-5 w-5 text-purple-500" />
          )}
          Trip Suggestions
        </CardTitle>
        <CardDescription>
          {showMemoryBased && memoryBasedSuggestions.length > 0
            ? "Personalized recommendations based on your travel history"
            : "AI-powered travel recommendations"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {filteredSuggestions.length === 0 ? (
          showEmpty ? (
            <EmptyState />
          ) : (
            <p className="text-center py-4 text-sm text-muted-foreground">
              No suggestions available.
            </p>
          )
        ) : (
          <div className="space-y-4">
            {/* Memory-based suggestions with special styling */}
            {memoryBasedSuggestions.length > 0 && (
              <>
                <div className="flex items-center gap-2 text-sm font-medium text-purple-600">
                  <Brain className="h-4 w-4" />
                  Personalized for You
                </div>
                {memoryBasedSuggestions.slice(0, 2).map((suggestion) => (
                  <div key={suggestion.id} className="relative">
                    <div className="absolute -top-2 -right-2 z-10">
                      <Badge className="bg-purple-100 text-purple-700 border-purple-200">
                        <Sparkles className="h-3 w-3 mr-1" />
                        AI Match
                      </Badge>
                    </div>
                    <div className="border border-purple-200 rounded-lg bg-purple-50/30">
                      <SuggestionCard suggestion={suggestion} />
                    </div>
                  </div>
                ))}
                {filteredSuggestions.length > memoryBasedSuggestions.length && (
                  <Separator className="my-4" />
                )}
              </>
            )}

            {/* Regular suggestions */}
            {filteredSuggestions
              .filter((s) => !s.id.startsWith("memory-"))
              .map((suggestion) => (
                <SuggestionCard key={suggestion.id} suggestion={suggestion} />
              ))}
          </div>
        )}
      </CardContent>
      {filteredSuggestions.length > 0 && (
        <CardFooter className="flex gap-2">
          <Button className="flex-1" variant="outline" asChild>
            <Link href="/chat">Get More Suggestions</Link>
          </Button>
          {showMemoryBased && (
            <Button className="flex-1" variant="outline" asChild>
              <Link href="/profile">
                <TrendingUp className="h-4 w-4 mr-2" />
                View Insights
              </Link>
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  );
}
