/**
 * @fileoverview Search analytics component showing user search patterns and trends.
 */

"use client";

import {
  BarChart3Icon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  PlaneIcon,
  TrendingUpIcon,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSearchHistoryStore } from "@/stores/search-history-store";

/** Props for the search analytics component */
interface SearchAnalyticsProps {
  className?: string;
  dateRange?: { start: string; end: string };
}

/** Search analytics component showing user search patterns and trends. */
export function SearchAnalytics({ className, dateRange }: SearchAnalyticsProps) {
  const [activeTab, setActiveTab] = useState("overview");

  /** Get search analytics and trends from store */
  const { getSearchAnalytics, getSearchTrends, recentSearches } =
    useSearchHistoryStore();

  /** Get search analytics and trends from store */
  const analytics = useMemo(
    () => getSearchAnalytics(dateRange),
    [getSearchAnalytics, dateRange]
  );
  const trends = useMemo(() => getSearchTrends(undefined, 14), [getSearchTrends]);

  /** Calculate peak search hours */
  const peakHours = useMemo(() => {
    const sortedHours = [...analytics.popularSearchTimes].sort(
      (a, b) => b.count - a.count
    );
    return sortedHours.slice(0, 3);
  }, [analytics.popularSearchTimes]);

  /** Format hour for display */
  const formatHour = (hour: number) => {
    if (hour === 0) return "12 AM";
    if (hour === 12) return "12 PM";
    return hour < 12 ? `${hour} AM` : `${hour - 12} PM`;
  };

  /** Get search type icon */
  const getSearchTypeIcon = (type: string) => {
    switch (type) {
      case "flight":
        return <PlaneIcon className="h-4 w-4" />;
      case "accommodation":
        return <MapPinIcon className="h-4 w-4" />;
      default:
        return <BarChart3Icon className="h-4 w-4" />;
    }
  };

  /** No recent searches */
  if (recentSearches.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3Icon className="h-4 w-4" />
            Search Analytics
          </CardTitle>
          <CardDescription>Start searching to see your travel patterns</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Your search analytics will appear here once you start exploring
            destinations.
          </p>
        </CardContent>
      </Card>
    );
  }

  /** Render search analytics */
  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <BarChart3Icon className="h-4 w-4" />
          Search Analytics
        </CardTitle>
        <CardDescription>Your travel search patterns and insights</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="times">Activity</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 mt-4">
            {/* Total Searches */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-2xl font-bold">{analytics.totalSearches}</p>
                <p className="text-xs text-muted-foreground">Total Searches</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-2xl font-bold">
                  {analytics.averageSearchDuration > 0
                    ? `${Math.round(analytics.averageSearchDuration / 1000)}s`
                    : "—"}
                </p>
                <p className="text-xs text-muted-foreground">Avg. Duration</p>
              </div>
            </div>

            {/* Search Types Breakdown */}
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                <TrendingUpIcon className="h-3 w-3" />
                Search Types
              </h4>
              <div className="space-y-2">
                {analytics.mostUsedSearchTypes.map((item) => (
                  <div key={item.type} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getSearchTypeIcon(item.type)}
                      <span className="text-sm capitalize">{item.type}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right">
                        {item.count}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Most Used Saved Searches */}
            {analytics.savedSearchUsage.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">Popular Saved Searches</h4>
                <div className="space-y-1">
                  {analytics.savedSearchUsage.slice(0, 3).map((search) => (
                    <div
                      key={search.searchId}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="truncate">{search.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {search.usageCount} uses
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="trends" className="space-y-4 mt-4">
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                <CalendarIcon className="h-3 w-3" />
                Last 14 Days
              </h4>
              <div className="flex items-end gap-1 h-24">
                {trends.map((day, index) => {
                  const maxCount = Math.max(...trends.map((t) => t.count), 1);
                  const height = (day.count / maxCount) * 100;
                  return (
                    <div
                      key={day.date}
                      className="flex-1 flex flex-col items-center"
                      title={`${day.date}: ${day.count} searches`}
                    >
                      <div
                        className={`w-full rounded-t ${
                          day.count > 0 ? "bg-primary" : "bg-muted"
                        }`}
                        style={{ height: `${Math.max(height, 4)}%` }}
                      />
                      {index % 2 === 0 && (
                        <span className="text-[10px] text-muted-foreground mt-1">
                          {new Date(day.date).getDate()}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground text-center mt-2">
                {trends.reduce((sum, t) => sum + t.count, 0)} searches in the last 2
                weeks
              </p>
            </div>
          </TabsContent>

          <TabsContent value="times" className="space-y-4 mt-4">
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                <ClockIcon className="h-3 w-3" />
                Peak Search Times
              </h4>
              {peakHours.length > 0 && peakHours[0].count > 0 ? (
                <div className="space-y-2">
                  {peakHours.map((hourData, index) => (
                    <div
                      key={hourData.hour}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-medium ${
                            index === 0 ? "text-primary" : "text-muted-foreground"
                          }`}
                        >
                          #{index + 1}
                        </span>
                        <span className="text-sm">{formatHour(hourData.hour)}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {hourData.count} searches
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Not enough data to show peak times yet.
                </p>
              )}
            </div>

            {/* 24-hour distribution mini chart */}
            <div>
              <h4 className="text-sm font-medium mb-2">Daily Distribution</h4>
              <div className="flex items-end gap-px h-16">
                {analytics.popularSearchTimes.map((hourData) => {
                  const maxCount = Math.max(
                    ...analytics.popularSearchTimes.map((h) => h.count),
                    1
                  );
                  const height = (hourData.count / maxCount) * 100;
                  return (
                    <div
                      key={hourData.hour}
                      className={`flex-1 rounded-t ${
                        hourData.count > 0 ? "bg-primary/60" : "bg-muted"
                      }`}
                      style={{ height: `${Math.max(height, 2)}%` }}
                      title={`${formatHour(hourData.hour)}: ${hourData.count} searches`}
                    />
                  );
                })}
              </div>
              <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                <span>12AM</span>
                <span>12PM</span>
                <span>11PM</span>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
