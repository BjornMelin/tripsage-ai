"use client";

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
import { Brain, Clock, MapPin, Sparkles, Star, TrendingUp } from "lucide-react";
import Link from "next/link";

interface TripSuggestionsProps {
  limit?: number;
  showEmpty?: boolean;
  userId?: string;
  showMemoryBased?: boolean;
}

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

function SuggestionCard({ suggestion }: { suggestion: TripSuggestion }) {
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

  const formatPrice = (price: number, currency: string) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 0,
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
        {suggestion.highlights.slice(0, 3).map((highlight, index) => (
          <Badge
            key={`highlight-${highlight}-${index}`}
            variant="outline"
            className="text-xs"
          >
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
        <Link href="/dashboard/chat">Chat with AI for Suggestions</Link>
      </Button>
    </div>
  );
}

export function TripSuggestions({
  limit = 4,
  showEmpty = true,
  userId,
  showMemoryBased = true,
}: TripSuggestionsProps) {
  const { activeBudget } = useBudgetStore();

  // Use React Query hook to fetch trip suggestions
  const { data: apiSuggestions, isLoading } = useTripSuggestions({
    limit: limit + 2, // Get extra in case we filter some out
    budget_max: activeBudget?.totalAmount,
  });

  // Memory-based recommendations
  const { data: memoryContext, isLoading: memoryLoading } = useMemoryContext(
    userId || "",
    !!userId && showMemoryBased
  );

  const { data: insights, isLoading: insightsLoading } = useMemoryInsights(
    userId || "",
    !!userId && showMemoryBased
  );

  // Generate memory-based suggestions
  const generateMemoryBasedSuggestions = (): TripSuggestion[] => {
    if (!memoryContext?.context || !insights?.insights) return [];

    const { userPreferences, travelPatterns } = memoryContext.context;
    const { recommendations, budgetPatterns, travelPersonality } = insights.insights;

    const memoryBasedSuggestions: TripSuggestion[] = [];

    // Add suggestions based on user preferences
    if (userPreferences.destinations) {
      userPreferences.destinations.slice(0, 2).forEach((dest, idx) => {
        memoryBasedSuggestions.push({
          id: `memory-dest-${idx}`,
          title: `Return to ${dest}`,
          destination: dest,
          description: `Based on your previous love for ${dest}, here's a personalized return trip.`,
          estimated_price: budgetPatterns?.averageSpending?.accommodation || 2000,
          currency: "USD",
          duration: 7,
          rating: 4.7,
          category:
            userPreferences.travel_style === "luxury" ? "relaxation" : "culture",
          best_time_to_visit: "Year-round",
          highlights: userPreferences.activities?.slice(0, 3) || ["Sightseeing"],
          trending: true,
        });
      });
    }

    // Add suggestions based on AI recommendations
    if (recommendations) {
      recommendations.slice(0, 2).forEach((rec, idx) => {
        if (rec.type === "destination") {
          memoryBasedSuggestions.push({
            id: `memory-ai-${idx}`,
            title: rec.recommendation,
            destination: rec.recommendation.split(" ")[0] || "Somewhere Amazing",
            description: rec.reasoning,
            estimated_price: budgetPatterns?.averageSpending?.total || 2500,
            currency: "USD",
            duration: 5,
            rating: 4.6,
            category: "adventure",
            best_time_to_visit: "Spring/Fall",
            highlights: ["AI Recommended", "Personalized"],
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
          {Array.from({ length: 2 }).map((_, i) => (
            <SuggestionCardSkeleton key={`skeleton-${i}`} />
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
            <Link href="/dashboard/chat">Get More Suggestions</Link>
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
