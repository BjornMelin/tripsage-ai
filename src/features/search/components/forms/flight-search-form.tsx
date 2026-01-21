/**
 * @fileoverview Flight search form component for searching flights.
 */

"use client";

import {
  type FlightSearchFormData,
  type FlightSearchParams as FlightSearchParamsSchema,
  flightSearchFormSchema,
  flightSearchParamsSchema,
} from "@schemas/search";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRightIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  PlaneIcon,
  SparklesIcon,
  UsersIcon,
} from "lucide-react";
import { useMemo } from "react";
import { z } from "zod";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useSearchHistoryStore } from "@/features/search/store/search-history";
import { keys } from "@/lib/keys";
import { cn } from "@/lib/utils";
import { buildRecentQuickSelectItems } from "../common/recent-items";
import { type QuickSelectItem, SearchFormShell } from "../common/search-form-shell";
import { useSearchForm } from "../common/use-search-form";

type FlightSearchFormValues = z.input<typeof flightSearchFormSchema>;

// Flight search params type
export type FlightSearchParams = FlightSearchFormData;

interface SearchSuggestion {
  id: string;
  type: "city" | "airport";
  name: string;
  code: string;
  country: string;
  popular?: boolean;
}

const PopularDestinationSchema = z.looseObject({
  code: z.string(),
  country: z.string().optional(),
  name: z.string(),
  savings: z.string().optional(),
});

const PopularDestinationsSchema = z.array(PopularDestinationSchema);

type PopularDestination = z.infer<typeof PopularDestinationSchema>;

const FALLBACK_POPULAR_DESTINATIONS: PopularDestination[] = [
  { code: "NYC", name: "New York", savings: "$127" },
  { code: "LAX", name: "Los Angeles", savings: "$89" },
  { code: "LHR", name: "London", savings: "$234" },
  { code: "NRT", name: "Tokyo", savings: "$298" },
];

const POPULAR_DESTINATION_SKELETON_KEYS = ["one", "two", "three", "four"] as const;

interface FlightSearchFormProps {
  onSearch: (params: FlightSearchParams) => Promise<void>;
  suggestions?: SearchSuggestion[];
  className?: string;
  showSmartBundles?: boolean;
  initialParams?: Partial<FlightSearchParams>;
}

/** Flight search form with validation and popular destination shortcuts. */
export function FlightSearchForm({
  onSearch,
  suggestions: _suggestions = [],
  className,
  showSmartBundles = true,
  initialParams,
}: FlightSearchFormProps) {
  const form = useSearchForm(
    flightSearchFormSchema,
    {
      cabinClass: "economy",
      departureDate: "",
      destination: "",
      directOnly: false,
      excludedAirlines: [],
      maxStops: undefined,
      origin: "",
      passengers: {
        adults: 1,
        children: 0,
        infants: 0,
      },
      preferredAirlines: [],
      returnDate: "",
      tripType: "round-trip",
      ...initialParams,
    },
    {}
  );

  const tripType = form.watch("tripType");
  const isRoundTrip = tripType === "round-trip";

  const { data: popularDestinations = [], isLoading: isLoadingPopularDestinations } =
    useQuery<PopularDestination[]>({
      gcTime: 2 * 60 * 60 * 1000, // 2 hours
      queryFn: async () => {
        const response = await fetch("/api/flights/popular-destinations");
        if (!response.ok) {
          throw new Error("Failed to fetch popular destinations");
        }
        const json: unknown = await response.json();
        const parsed = PopularDestinationsSchema.safeParse(json);
        if (!parsed.success) {
          throw new Error("Invalid popular destinations response");
        }
        return parsed.data;
      },
      queryKey: keys.flights.popularDestinations(),
      staleTime: 60 * 60 * 1000, // 1 hour
    });

  const destinationsToRender =
    popularDestinations.length > 0
      ? popularDestinations
      : FALLBACK_POPULAR_DESTINATIONS;

  const smartBundles = {
    car: "$89",
    hotel: "$156",
    total: "$245",
  };

  const handleSwapAirports = () => {
    const origin = form.getValues("origin");
    const destination = form.getValues("destination");

    form.setValue("origin", destination);
    form.setValue("destination", origin);
  };

  const popularItems: QuickSelectItem<FlightSearchFormValues>[] = useMemo(() => {
    if (isLoadingPopularDestinations) {
      return POPULAR_DESTINATION_SKELETON_KEYS.map((key) => ({
        description: "Fetching deals",
        disabled: true,
        id: `popular-destination-skeleton-${key}`,
        label: "Loading…",
        params: {},
      }));
    }

    return destinationsToRender.map((dest) => ({
      description: dest.savings ? `Save ${dest.savings}` : "Popular now",
      id: dest.code,
      label: dest.name,
      params: { destination: dest.code },
    }));
  }, [destinationsToRender, isLoadingPopularDestinations]);

  const recentSearchesByType = useSearchHistoryStore(
    (state) => state.recentSearchesByType.flight
  );
  const recentSearches = useMemo(
    () => recentSearchesByType.slice(0, 4),
    [recentSearchesByType]
  );
  const recentItems: QuickSelectItem<FlightSearchFormValues>[] = useMemo(() => {
    return buildRecentQuickSelectItems<
      FlightSearchFormValues,
      FlightSearchParamsSchema
    >(recentSearches, flightSearchParamsSchema, (params, search) => {
      const passengers = params.passengers ?? {
        adults: params.adults ?? 1,
        children: params.children ?? 0,
        infants: params.infants ?? 0,
      };

      const tripTypeValue: FlightSearchFormData["tripType"] = params.returnDate
        ? "round-trip"
        : "one-way";

      const label = [
        params.origin ?? "Origin",
        "→",
        params.destination ?? "Destination",
      ].join(" ");

      const description = params.departureDate
        ? params.returnDate
          ? `${params.departureDate} → ${params.returnDate}`
          : params.departureDate
        : undefined;

      const item: QuickSelectItem<FlightSearchFormValues> = {
        id: search.id,
        label,
        params: {
          cabinClass: params.cabinClass ?? "economy",
          departureDate: params.departureDate ?? "",
          destination: params.destination ?? "",
          directOnly: params.directOnly ?? false,
          excludedAirlines: params.excludedAirlines ?? [],
          maxStops: params.maxStops,
          origin: params.origin ?? "",
          passengers,
          preferredAirlines: params.preferredAirlines ?? [],
          returnDate: params.returnDate ?? "",
          tripType: tripTypeValue,
        },
        ...(description ? { description } : {}),
      };

      return item;
    });
  }, [recentSearches]);

  return (
    <Card className={cn("w-full max-w-4xl mx-auto", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <PlaneIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-xl">Find Flights</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Search and compare flights from top airlines
              </p>
            </div>
          </div>

          {showSmartBundles && (
            <div className="hidden md:flex items-center gap-2">
              <Badge
                variant="secondary"
                className="bg-green-50 text-green-700 border-green-200"
              >
                <SparklesIcon className="h-3 w-3 mr-1" />
                Smart Bundle: Save up to {smartBundles.total}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <SearchFormShell
          form={form}
          onSubmit={onSearch}
          telemetrySpanName="search.flight.form.submit"
          telemetryAttributes={{ searchType: "flight" }}
          telemetryErrorMetadata={{
            action: "submit",
            context: "FlightSearchForm",
          }}
          submitLabel="Search Flights"
          loadingLabel="Searching flights…"
          disableSubmitWhenInvalid
          className="space-y-6"
          popularItems={popularItems}
          popularLabel="Popular destinations"
          recentItems={recentItems}
          secondaryAction={
            <Button
              variant="outline"
              size="lg"
              className="w-full sm:w-auto px-6"
              type="button"
            >
              <ClockIcon className="h-4 w-4 mr-2" />
              Flexible Dates
            </Button>
          }
          footer={
            showSmartBundles
              ? (_form, _state) => (
                  <>
                    <Separator />
                    <div className="bg-gradient-to-r from-blue-50 to-green-50 p-4 rounded-lg border">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <SparklesIcon className="h-5 w-5 text-blue-600" />
                          <h3 className="font-semibold text-sm">Smart Trip Bundle</h3>
                          <Badge
                            variant="secondary"
                            className="bg-green-100 text-green-700"
                          >
                            Save {smartBundles.total}
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          vs booking separately
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div className="text-center">
                          <div className="font-medium">Flight + Hotel</div>
                          <div className="text-green-600 font-semibold">
                            Save {smartBundles.hotel}
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="font-medium">+ Car Rental</div>
                          <div className="text-green-600 font-semibold">
                            Save {smartBundles.car}
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="font-medium">Total Savings</div>
                          <div className="text-green-600 font-semibold text-lg">
                            {smartBundles.total}
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                )
              : undefined
          }
        >
          {(form, state) => (
            <>
              <FormField
                control={form.control}
                name="tripType"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex gap-2">
                      {(["round-trip", "one-way", "multi-city"] as const).map(
                        (type) => (
                          <Button
                            key={type}
                            type="button"
                            variant={field.value === type ? "default" : "outline"}
                            size="sm"
                            onClick={() => field.onChange(type)}
                            className="capitalize"
                            disabled={state.isSubmitting}
                          >
                            {type === "round-trip"
                              ? "Round Trip"
                              : type === "one-way"
                                ? "One Way"
                                : "Multi-City"}
                          </Button>
                        )
                      )}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                <div className="lg:col-span-6 grid grid-cols-1 md:grid-cols-2 gap-4 relative">
                  <FormField
                    control={form.control}
                    name="origin"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">From</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <MapPinIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                              placeholder="Departure city or airport"
                              className="pl-10"
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="hidden md:flex absolute left-1/2 top-8 transform -translate-x-1/2 z-10">
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={handleSwapAirports}
                      disabled={state.isSubmitting}
                      className="rounded-full bg-background border-2 shadow-md hover:shadow-lg transition-shadow"
                    >
                      <ArrowRightIcon className="h-4 w-4" />
                    </Button>
                  </div>

                  <FormField
                    control={form.control}
                    name="destination"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">To</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <MapPinIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                              placeholder="Destination city or airport"
                              className="pl-10"
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="lg:col-span-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="departureDate"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">Departure</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <CalendarIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input type="date" className="pl-10" {...field} />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {isRoundTrip && (
                    <FormField
                      control={form.control}
                      name="returnDate"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-sm font-medium">Return</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <CalendarIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                              <Input type="date" className="pl-10" {...field} />
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}
                </div>

                <div className="lg:col-span-2 space-y-4">
                  <FormField
                    control={form.control}
                    name="passengers.adults"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">Adults</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <UsersIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Select
                              value={field.value.toString()}
                              onValueChange={(value) =>
                                field.onChange(Number.parseInt(value, 10))
                              }
                            >
                              <SelectTrigger className="pl-10">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
                                  <SelectItem key={num} value={num.toString()}>
                                    {num} {num === 1 ? "Adult" : "Adults"}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="passengers.children"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">
                          Children (2-11)
                        </FormLabel>
                        <FormControl>
                          <Select
                            value={field.value.toString()}
                            onValueChange={(value) =>
                              field.onChange(Number.parseInt(value, 10))
                            }
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((num) => (
                                <SelectItem key={num} value={num.toString()}>
                                  {num} {num === 1 ? "Child" : "Children"}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="cabinClass"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">Class</FormLabel>
                        <FormControl>
                          <Select value={field.value} onValueChange={field.onChange}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="economy">Economy</SelectItem>
                              <SelectItem value="premium_economy">
                                Premium Economy
                              </SelectItem>
                              <SelectItem value="business">Business</SelectItem>
                              <SelectItem value="first">First Class</SelectItem>
                            </SelectContent>
                          </Select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            </>
          )}
        </SearchFormShell>
      </CardContent>
    </Card>
  );
}
