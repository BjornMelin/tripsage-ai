/**
 * @fileoverview Client-side search hub experience (renders within RSC shell).
 */

"use client";

import type { SearchType } from "@schemas/search";
import {
  ClockIcon,
  HistoryIcon,
  HotelIcon,
  MapPinIcon,
  PlaneIcon,
  RefreshCwIcon,
  SearchIcon,
  SparklesIcon,
} from "lucide-react";
import Link from "next/link";
import type React from "react";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SearchAnalytics } from "@/features/search/components/search-analytics";
import { SearchCollections } from "@/features/search/components/search-collections";
import { useSearchHistoryStore } from "@/features/search/store/search-history/index";
import { ROUTES } from "@/lib/routes";

type RepeatSearchParams = Record<string, string | number | boolean | null | undefined>;

/** Get the base path for a search type. */
function getSearchPath(searchType: SearchType): string {
  switch (searchType) {
    case "flight":
      return `${ROUTES.dashboard.search}/flights`;
    case "accommodation":
      return `${ROUTES.dashboard.search}/hotels`;
    case "activity":
      return `${ROUTES.dashboard.search}/activities`;
    case "destination":
      return `${ROUTES.dashboard.search}/destinations`;
    default:
      return ROUTES.dashboard.search;
  }
}

/** Search hub client component. */
export default function SearchHubClient() {
  const { recentSearches } = useSearchHistoryStore();

  // Get the 6 most recent searches
  const displayedSearches = recentSearches.slice(0, 6);

  /**
   * Navigate to search page with parameters.
   *
   * @param searchType - The type of search to repeat.
   * @param params - The parameters to repeat the search with.
   * @returns void
   */
  const getRepeatSearchHref = (
    searchType: SearchType,
    params: RepeatSearchParams
  ): string => {
    const basePath = getSearchPath(searchType);
    const queryParams = new URLSearchParams();

    // Map params to query string based on search type
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        queryParams.append(key, String(value));
      }
    }

    const url = queryParams.toString()
      ? `${basePath}?${queryParams.toString()}`
      : basePath;
    return url;
  };

  return (
    <SearchLayout>
      <TooltipProvider>
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main content - 2 columns */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="w-full">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <SearchIcon aria-hidden="true" className="h-5 w-5" />
                  Search Options
                </CardTitle>
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
                        href={`${ROUTES.dashboard.search}/flights`}
                        icon={<PlaneIcon aria-hidden="true" className="h-5 w-5" />}
                      />
                      <SearchQuickOptionCard
                        title="Book Hotels"
                        description="Find accommodations for your stay"
                        href={`${ROUTES.dashboard.search}/hotels`}
                        icon={<HotelIcon aria-hidden="true" className="h-5 w-5" />}
                      />
                      <SearchQuickOptionCard
                        title="Discover Activities"
                        description="Explore things to do at your destination"
                        href={`${ROUTES.dashboard.search}/activities`}
                        icon={<SparklesIcon aria-hidden="true" className="h-5 w-5" />}
                      />
                      <SearchQuickOptionCard
                        title="Browse Destinations"
                        description="Get inspired for your next trip"
                        href={`${ROUTES.dashboard.search}/destinations`}
                        icon={<MapPinIcon aria-hidden="true" className="h-5 w-5" />}
                      />
                    </div>
                  </TabsContent>
                  <TabsContent value="flights" className="py-4">
                    <Card className="bg-muted/50">
                      <CardContent className="flex items-center justify-between py-4">
                        <div className="flex items-center gap-3">
                          <div className="rounded-full bg-primary/10 p-2">
                            <PlaneIcon
                              aria-hidden="true"
                              className="h-5 w-5 text-primary"
                            />
                          </div>
                          <div>
                            <p className="font-medium">Flight Search</p>
                            <p className="text-sm text-muted-foreground">
                              Find the best flight deals
                            </p>
                          </div>
                        </div>
                        <Button asChild>
                          <Link href={`${ROUTES.dashboard.search}/flights`}>
                            Search Flights
                          </Link>
                        </Button>
                      </CardContent>
                    </Card>
                  </TabsContent>
                  <TabsContent value="hotels" className="py-4">
                    <Card className="bg-muted/50">
                      <CardContent className="flex items-center justify-between py-4">
                        <div className="flex items-center gap-3">
                          <div className="rounded-full bg-primary/10 p-2">
                            <HotelIcon
                              aria-hidden="true"
                              className="h-5 w-5 text-primary"
                            />
                          </div>
                          <div>
                            <p className="font-medium">Hotel Search</p>
                            <p className="text-sm text-muted-foreground">
                              Find accommodations worldwide
                            </p>
                          </div>
                        </div>
                        <Button asChild>
                          <Link href={`${ROUTES.dashboard.search}/hotels`}>
                            Search Hotels
                          </Link>
                        </Button>
                      </CardContent>
                    </Card>
                  </TabsContent>
                  <TabsContent value="activities" className="py-4">
                    <Card className="bg-muted/50">
                      <CardContent className="flex items-center justify-between py-4">
                        <div className="flex items-center gap-3">
                          <div className="rounded-full bg-primary/10 p-2">
                            <SparklesIcon
                              aria-hidden="true"
                              className="h-5 w-5 text-primary"
                            />
                          </div>
                          <div>
                            <p className="font-medium">Activity Search</p>
                            <p className="text-sm text-muted-foreground">
                              Discover things to do
                            </p>
                          </div>
                        </div>
                        <Button asChild>
                          <Link href={`${ROUTES.dashboard.search}/activities`}>
                            Search Activities
                          </Link>
                        </Button>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            <Card className="w-full">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <HistoryIcon aria-hidden="true" className="h-5 w-5" />
                  Recent Searches
                </CardTitle>
                <CardDescription>Your most recent search queries</CardDescription>
              </CardHeader>
              <CardContent>
                {displayedSearches.length === 0 ? (
                  <div className="text-center py-8">
                    <div className="rounded-full bg-muted p-4 w-fit mx-auto mb-4">
                      <SearchIcon
                        aria-hidden="true"
                        className="h-8 w-8 text-muted-foreground"
                      />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      No recent searches yet. Start exploring to build your search
                      history!
                    </p>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {displayedSearches.map((search) => {
                      const safeParams = Object.fromEntries(
                        Object.entries(search.params).filter(
                          ([_key, value]) =>
                            value == null ||
                            ["string", "number", "boolean"].includes(typeof value)
                        )
                      ) as RepeatSearchParams;
                      return (
                        <RecentSearchCard
                          key={search.id}
                          title={getSearchTitle(search.params)}
                          type={search.searchType}
                          date={new Date(search.timestamp).toLocaleDateString()}
                          href={getRepeatSearchHref(search.searchType, safeParams)}
                        />
                      );
                    })}
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
      </TooltipProvider>
    </SearchLayout>
  );
}

/** Get the title of a search based on its parameters. */
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

/** Get the icon for a search type. */
function getSearchTypeIcon(type: SearchType): React.ReactNode {
  switch (type) {
    case "flight":
      return <PlaneIcon aria-hidden="true" className="h-3 w-3" />;
    case "accommodation":
      return <HotelIcon aria-hidden="true" className="h-3 w-3" />;
    case "activity":
      return <SparklesIcon aria-hidden="true" className="h-3 w-3" />;
    case "destination":
      return <MapPinIcon aria-hidden="true" className="h-3 w-3" />;
    default:
      return <SearchIcon aria-hidden="true" className="h-3 w-3" />;
  }
}

/** Quick option card for search types. */
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
    <Tooltip>
      <TooltipTrigger asChild>
        <Link href={href} className="block">
          <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer group">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <div className="rounded-full bg-primary/10 p-2 group-hover:bg-primary/20 transition-colors">
                  {icon}
                </div>
                {title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{description}</p>
            </CardContent>
          </Card>
        </Link>
      </TooltipTrigger>
      <TooltipContent>Click to {title.toLowerCase()}</TooltipContent>
    </Tooltip>
  );
}

/** Recent search card. */
function RecentSearchCard({
  title,
  type,
  date,
  href,
}: {
  title: string;
  type: SearchType;
  date: string;
  href: string;
}) {
  return (
    <Card className="h-full hover:bg-accent/50 transition-colors group">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center gap-2">
          <CardTitle className="text-base truncate flex-1">{title}</CardTitle>
          <Badge
            variant="secondary"
            className="shrink-0 text-xs flex items-center gap-1"
          >
            {getSearchTypeIcon(type)}
            {type}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between items-center">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <ClockIcon aria-hidden="true" className="h-3 w-3" />
            {date}
          </p>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-auto py-1 px-2 text-primary"
                asChild
              >
                <Link href={href}>
                  <RefreshCwIcon aria-hidden="true" className="h-3 w-3 mr-1" />
                  Search again
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Repeat this search</TooltipContent>
          </Tooltip>
        </div>
      </CardContent>
    </Card>
  );
}
