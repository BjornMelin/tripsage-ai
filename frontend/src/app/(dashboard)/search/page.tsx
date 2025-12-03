/**
 * @fileoverview Client page for searching flights, hotels, activities, or destinations.
 */

"use client";

import {
  HistoryIcon,
  HotelIcon,
  MapPinIcon,
  PlaneIcon,
  SparklesIcon,
} from "lucide-react";
import Link from "next/link";
import type React from "react";
import { SearchAnalytics, SearchCollections } from "@/components/features/search";
import { SearchLayout } from "@/components/layouts/search-layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSearchHistoryStore } from "@/stores/search-history-store";

/** Client page for searching flights, hotels, activities, or destinations. */
export default function SearchPage() {
  const { recentSearches } = useSearchHistoryStore();

  // Get the 6 most recent searches
  const displayedSearches = recentSearches.slice(0, 6);

  return (
    <SearchLayout>
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main content - 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="w-full">
            <CardHeader>
              <CardTitle>Search Options</CardTitle>
              <CardDescription>
                Start your search for flights, hotels, activities or destinations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="all" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="flights">Flights</TabsTrigger>
                  <TabsTrigger value="hotels">Hotels</TabsTrigger>
                  <TabsTrigger value="activities">Activities</TabsTrigger>
                </TabsList>
                <TabsContent value="all" className="py-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <SearchQuickOptionCard
                      title="Find Flights"
                      description="Search for flights to any destination"
                      href="/dashboard/search/flights"
                      icon={<PlaneIcon className="h-5 w-5" />}
                    />
                    <SearchQuickOptionCard
                      title="Book Hotels"
                      description="Find accommodations for your stay"
                      href="/dashboard/search/hotels"
                      icon={<HotelIcon className="h-5 w-5" />}
                    />
                    <SearchQuickOptionCard
                      title="Discover Activities"
                      description="Explore things to do at your destination"
                      href="/dashboard/search/activities"
                      icon={<SparklesIcon className="h-5 w-5" />}
                    />
                    <SearchQuickOptionCard
                      title="Browse Destinations"
                      description="Get inspired for your next trip"
                      href="/dashboard/search/destinations"
                      icon={<MapPinIcon className="h-5 w-5" />}
                    />
                  </div>
                </TabsContent>
                <TabsContent value="flights" className="py-4">
                  <Link
                    href="/dashboard/search/flights"
                    className="text-primary hover:underline"
                  >
                    Go to Flights Search →
                  </Link>
                </TabsContent>
                <TabsContent value="hotels" className="py-4">
                  <Link
                    href="/dashboard/search/hotels"
                    className="text-primary hover:underline"
                  >
                    Go to Hotels Search →
                  </Link>
                </TabsContent>
                <TabsContent value="activities" className="py-4">
                  <Link
                    href="/dashboard/search/activities"
                    className="text-primary hover:underline"
                  >
                    Go to Activities Search →
                  </Link>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <Card className="w-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HistoryIcon className="h-5 w-5" />
                Recent Searches
              </CardTitle>
              <CardDescription>Your most recent search queries</CardDescription>
            </CardHeader>
            <CardContent>
              {displayedSearches.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No recent searches yet. Start exploring to build your search history!
                </p>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {displayedSearches.map((search) => (
                    <RecentSearchCard
                      key={search.id}
                      title={getSearchTitle(search.params)}
                      type={search.searchType}
                      date={new Date(search.timestamp).toLocaleDateString()}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - 1 column */}
        <div className="space-y-6">
          <SearchAnalytics />
          <SearchCollections />
        </div>
      </div>
    </SearchLayout>
  );
}

/**
 * Get the title of a search based on its parameters
 *
 * @param params - The parameters of the search
 * @returns The title of the search
 */
function getSearchTitle(params: Record<string, unknown>): string {
  const origin = params.origin as string | undefined;
  const destination = params.destination as string | undefined;
  const location = params.location as string | undefined;
  const query = params.query as string | undefined;

  if (origin && destination) {
    return `${origin} to ${destination}`;
  }
  if (destination) {
    return destination;
  }
  if (location) {
    return location;
  }
  if (query) {
    return query;
  }
  return "Search";
}

/**
 * Quick option card for search types
 *
 * @param title - The title of the card
 * @param description - The description of the card
 * @param href - The href of the card
 * @param icon - The icon of the card
 * @returns A React component that displays a quick option card
 */
function SearchQuickOptionCard({
  title,
  description,
  href,
  icon,
}: {
  title: string;
  description: string;
  href: string;
  icon?: React.ReactNode;
}) {
  return (
    <a href={href} className="block">
      <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            {icon}
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{description}</p>
        </CardContent>
      </Card>
    </a>
  );
}

/**
 * Recent search card
 *
 * @param title - The title of the card
 * @param type - The type of the card
 * @param date - The date of the card
 * @returns A React component that displays a recent search card
 */
function RecentSearchCard({
  title,
  type,
  date,
}: {
  title: string;
  type: string;
  date: string;
}) {
  return (
    <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-base">{title}</CardTitle>
          <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full">
            {type}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between items-center">
          <p className="text-xs text-muted-foreground">{date}</p>
          <button type="button" className="text-xs text-primary">
            Search again
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
