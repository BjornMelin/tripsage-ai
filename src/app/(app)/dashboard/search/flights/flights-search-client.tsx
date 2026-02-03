/**
 * @fileoverview Client-side flight search experience (renders within RSC shell).
 */

"use client";

import type { FlightSearchParams } from "@schemas/search";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRightIcon,
  InfoIcon,
  LightbulbIcon,
  PlaneIcon,
  TrendingUpIcon,
} from "lucide-react";

import { useRouter } from "next/navigation";
import React from "react";
import { z } from "zod";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/use-toast";
import { buildFlightApiPayload } from "@/features/search/components/filters/api-payload";
import { FilterPanel } from "@/features/search/components/filters/filter-panel";
import { FilterPresets } from "@/features/search/components/filters/filter-presets";
import { FlightSearchForm } from "@/features/search/components/forms/flight-search-form";
import { useSearchOrchestration } from "@/features/search/hooks/search/use-search-orchestration";
import { useSearchFiltersStore } from "@/features/search/store/search-filters-store";
import { getErrorMessage } from "@/lib/api/error-types";
import { keys } from "@/lib/keys";
import type { Result, ResultError } from "@/lib/result";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

/** Flight search client component props. */
interface FlightsSearchClientProps {
  initialUrlParams?: {
    /** Cabin class query param. */
    class?: string;
    departDate?: string;
    destination?: string;
    origin?: string;
    passengers?: string;
    returnDate?: string;
  };
  onSubmitServer: (
    params: FlightSearchParams
  ) => Promise<Result<FlightSearchParams, ResultError>>;
}

const FLIGHT_URL_CABIN_SCHEMA = z.enum([
  "economy",
  "premium_economy",
  "business",
  "first",
]);
const FLIGHT_URL_DATE_SCHEMA = z.preprocess((value) => {
  if (typeof value !== "string" || value.trim() === "") return undefined;
  return Number.isNaN(Date.parse(value)) ? undefined : value;
}, z.string().optional());
const POPULAR_ROUTE_SCHEMA = z.strictObject({
  date: z.string().min(1),
  destination: z.string().min(1),
  origin: z.string().min(1),
  price: z.number().int().nonnegative(),
});
const POPULAR_ROUTES_SCHEMA = z.array(POPULAR_ROUTE_SCHEMA);
type PopularRoute = z.infer<typeof POPULAR_ROUTE_SCHEMA>;
const FLIGHT_URL_PARAMS_SCHEMA = z.strictObject({
  cabinClass: z.preprocess(
    (value) => (typeof value === "string" && value ? value : undefined),
    FLIGHT_URL_CABIN_SCHEMA.optional()
  ),
  departDate: FLIGHT_URL_DATE_SCHEMA,
  destination: z.preprocess(
    (value) => (typeof value === "string" && value ? value : undefined),
    z.string().min(1).optional()
  ),
  origin: z.preprocess(
    (value) => (typeof value === "string" && value ? value : undefined),
    z.string().min(1).optional()
  ),
  passengers: z.preprocess((value) => {
    if (typeof value !== "string" || value.trim() === "") return undefined;
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return undefined;
    return parsed;
  }, z.number().int().min(1).max(9).default(1)),
  returnDate: FLIGHT_URL_DATE_SCHEMA,
});

/**
 * Flight search client component.
 * @param initialUrlParams - The initial URL params.
 * @param onSubmitServer - The server-side submit function.
 * @returns The flight search client.
 */
export default function FlightsSearchClient({
  initialUrlParams,
  onSubmitServer,
}: FlightsSearchClientProps) {
  const { initializeSearch, executeSearch } = useSearchOrchestration();
  const router = useRouter();
  const { toast } = useToast();
  const activeFilters = useSearchFiltersStore((s) => s.activeFilters);
  const currentSearchController = React.useRef<AbortController | null>(null);
  const didInitFromUrlParams = React.useRef(false);
  const {
    data: popularRoutes = [],
    isError: popularRoutesError,
    isLoading: popularRoutesLoading,
  } = useQuery<PopularRoute[]>({
    queryFn: async () => {
      const response = await fetch("/api/flights/popular-routes");
      if (!response.ok) {
        throw new Error("Failed to fetch popular routes");
      }
      const json: unknown = await response.json();
      return POPULAR_ROUTES_SCHEMA.parse(json);
    },
    queryKey: keys.flights.popularRoutes(),
    staleTime: 60 * 60 * 1000, // 1 hour
  });

  React.useEffect(() => {
    return () => {
      currentSearchController.current?.abort();
      currentSearchController.current = null;
    };
  }, []);

  React.useEffect(() => {
    initializeSearch("flight");
  }, [initializeSearch]);

  React.useEffect(() => {
    if (didInitFromUrlParams.current) return;
    didInitFromUrlParams.current = true;

    const controller = new AbortController();

    const parsed = FLIGHT_URL_PARAMS_SCHEMA.safeParse({
      cabinClass: initialUrlParams?.class,
      departDate: initialUrlParams?.departDate,
      destination: initialUrlParams?.destination,
      origin: initialUrlParams?.origin,
      passengers: initialUrlParams?.passengers,
      returnDate: initialUrlParams?.returnDate,
    });

    if (
      parsed.success &&
      (parsed.data.origin || parsed.data.destination || parsed.data.departDate)
    ) {
      const initialParams: FlightSearchParams = {
        adults: parsed.data.passengers,
        cabinClass: parsed.data.cabinClass ?? "economy",
        departureDate: parsed.data.departDate,
        destination: parsed.data.destination,
        origin: parsed.data.origin,
        returnDate: parsed.data.returnDate,
      };
      // Server-side telemetry then client execution
      onSubmitServer(initialParams)
        .then(async (validatedParams) => {
          if (controller.signal.aborted) return;
          if (!validatedParams.ok) {
            toast({
              description: validatedParams.error.reason,
              title: "Search Failed",
              variant: "destructive",
            });
            return;
          }

          await executeSearch(validatedParams.data, controller.signal);
        })
        .catch((error) => {
          if (controller.signal.aborted) return;
          if (error instanceof Error && error.name === "AbortError") return;
          toast({
            description: getErrorMessage(error),
            title: "Search Failed",
            variant: "destructive",
          });
        });
    }

    return () => controller.abort();
  }, [executeSearch, initialUrlParams, onSubmitServer, toast]);

  const handleSearch = async (params: FlightSearchParams) => {
    currentSearchController.current?.abort();
    const controller = new AbortController();
    currentSearchController.current = controller;
    try {
      // Merge form params with active filter payload
      const filterPayload = buildFlightApiPayload(activeFilters);
      const searchWithFilters: FlightSearchParams = {
        ...params,
        ...filterPayload,
      };
      const validatedParams = await onSubmitServer(searchWithFilters); // server-side telemetry and validation
      if (controller.signal.aborted) return;
      if (!validatedParams.ok) {
        toast({
          description: validatedParams.error.reason,
          title: "Search Failed",
          variant: "destructive",
        });
        return;
      }

      const searchId = await executeSearch(validatedParams.data, controller.signal);
      if (controller.signal.aborted) return;
      if (searchId) {
        toast({
          description: "Searching for flights…",
          title: "Search Started",
        });
        router.push(`${ROUTES.searchFlightsResults}?searchId=${searchId}`);
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      if (error instanceof Error && error.name === "AbortError") return;
      toast({
        description: getErrorMessage(error),
        title: "Search Failed",
        variant: "destructive",
      });
    } finally {
      if (currentSearchController.current === controller) {
        currentSearchController.current = null;
      }
    }
  };

  return (
    <SearchLayout>
      <TooltipProvider>
        <div className="grid gap-6 lg:grid-cols-4">
          {/* Main content - 3 columns */}
          <div className="lg:col-span-3 space-y-6">
            {/* Search Form */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PlaneIcon className="h-5 w-5" />
                  Search Flights
                </CardTitle>
                <CardDescription>
                  Find the best flight deals to your destination
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FlightSearchForm onSearch={handleSearch} />
              </CardContent>
            </Card>

            {/* Popular Routes */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUpIcon className="h-5 w-5" />
                  Popular Routes
                </CardTitle>
                <CardDescription>Trending flight routes and deals</CardDescription>
              </CardHeader>
              <CardContent>
                {popularRoutesLoading ? (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {["sk-1", "sk-2", "sk-3", "sk-4", "sk-5", "sk-6"].map((key) => (
                      <Card key={key} className="animate-pulse">
                        <CardContent className="p-4 space-y-3">
                          <div className="h-4 w-3/4 rounded bg-muted" />
                          <div className="h-3 w-1/2 rounded bg-muted" />
                          <div className="h-8 w-full rounded bg-muted" />
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : popularRoutesError ? (
                  <div className="text-sm text-muted-foreground">
                    Unable to load popular routes right now.
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {popularRoutes.map((route) => (
                      <PopularRouteCard
                        key={`${route.origin}-${route.destination}-${route.date}`}
                        {...route}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Travel Tips */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LightbulbIcon className="h-5 w-5" />
                  Travel Tips
                </CardTitle>
                <CardDescription>
                  Tips to help you find the best flights
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <TravelTip
                    title="Book 1-3 months in advance for the best prices"
                    description="Studies show that booking domestic flights about 1-3 months in advance and international flights 2-8 months in advance typically yields the best prices."
                  />
                  <Separator />
                  <TravelTip
                    title="Consider nearby airports"
                    description="Flying to or from a nearby airport can sometimes save you hundreds of dollars. Our search automatically checks nearby airports too."
                  />
                  <Separator />
                  <TravelTip
                    title="Be flexible with dates if possible"
                    description="Prices can vary significantly from one day to the next. Use our flexible dates option to see prices across multiple days and find the best deal."
                  />
                  <Separator />
                  <TravelTip
                    title="Set price alerts for your routes"
                    description="If your travel dates are still far out, set up price alerts to be notified when prices drop for your specific routes."
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - 1 column */}
          <div className="space-y-6">
            <FilterPanel />
            <FilterPresets />
          </div>
        </div>
      </TooltipProvider>
    </SearchLayout>
  );
}

/** Card component for displaying a popular route. */
function PopularRouteCard({
  origin,
  destination,
  price,
  date,
  onSelect,
}: {
  origin: string;
  destination: string;
  price: number;
  date: string;
  onSelect?: () => void;
}) {
  const card = (
    <Card
      className={cn(
        "h-full transition-colors",
        onSelect && "hover:bg-accent/50 cursor-pointer"
      )}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (!onSelect) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      role={onSelect ? "button" : undefined}
      tabIndex={onSelect ? 0 : undefined}
    >
      <CardContent className="p-4">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="font-medium flex items-center gap-2">
              {origin}
              <ArrowRightIcon className="h-4 w-4 text-muted-foreground" />
              {destination}
            </h3>
            <p className="text-xs text-muted-foreground mt-1">{date}</p>
          </div>
          <div className="text-right">
            <span className="font-semibold text-lg">${price}</span>
            <p className="text-xs text-muted-foreground">roundtrip</p>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <Badge variant="secondary" className="text-xs">
            <PlaneIcon className="h-3 w-3 mr-1" />
            Deal
          </Badge>
          {onSelect ? (
            <span className="text-xs text-primary font-medium">View Deal →</span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );

  if (!onSelect) {
    return card;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{card}</TooltipTrigger>
      <TooltipContent>
        Click to search {origin} to {destination}
      </TooltipContent>
    </Tooltip>
  );
}

/**
 * Component for displaying a travel tip.
 */
function TravelTip({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex gap-4">
      <div className="shrink-0">
        <div className="rounded-full bg-primary/10 p-2">
          <InfoIcon className="h-4 w-4 text-primary" />
        </div>
      </div>
      <div>
        <h3 className="font-medium mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
