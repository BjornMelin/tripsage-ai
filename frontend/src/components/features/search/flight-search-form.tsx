/**
 * @fileoverview Flight search form component for searching flights.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { type FlightSearchFormData, flightSearchFormSchema } from "@schemas/search";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  Clock,
  Loader2,
  MapPin,
  Plane,
  Search,
  Sparkles,
  TrendingDown,
  Users,
} from "lucide-react";
import React, { useOptimistic, useState, useTransition } from "react";
import { useForm } from "react-hook-form";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";

// Use validated flight search params from schemas
export type ModernFlightSearchParams = FlightSearchFormData;

interface SearchSuggestion {
  id: string;
  type: "city" | "airport";
  name: string;
  code: string;
  country: string;
  popular?: boolean;
}

interface PopularDestination {
  code: string;
  name: string;
  savings?: string;
  country?: string;
}

const POPULAR_DESTINATIONS_QUERY_KEY = ["flights", "popular-destinations"] as const;

const FALLBACK_POPULAR_DESTINATIONS: PopularDestination[] = [
  { code: "NYC", name: "New York", savings: "$127" },
  { code: "LAX", name: "Los Angeles", savings: "$89" },
  { code: "LHR", name: "London", savings: "$234" },
  { code: "NRT", name: "Tokyo", savings: "$298" },
];

const POPULAR_DESTINATION_SKELETON_KEYS = ["one", "two", "three", "four"] as const;

interface FlightSearchFormProps {
  onSearch: (params: ModernFlightSearchParams) => Promise<void>;
  suggestions?: SearchSuggestion[];
  className?: string;
  showSmartBundles?: boolean;
  initialParams?: Partial<ModernFlightSearchParams>;
}

/** Flight search form with validation and popular destination shortcuts. */
export function FlightSearchForm({
  onSearch,
  suggestions: _suggestions = [],
  className,
  showSmartBundles = true,
  initialParams,
}: FlightSearchFormProps) {
  const [isPending, startTransition] = useTransition();
  const [formError, setFormError] = useState<string | null>(null);

  // React Hook Form with Zod validation
  const form = useForm<ModernFlightSearchParams>({
    defaultValues: {
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
    mode: "onChange",
    resolver: zodResolver(flightSearchFormSchema),
  });

  // Watch form values for dynamic behavior
  const tripType = form.watch("tripType");
  const isRoundTrip = tripType === "round-trip";

  // Optimistic search state
  const [optimisticSearching, setOptimisticSearching] = useOptimistic(
    false,
    (_state, isSearching: boolean) => isSearching
  );

  const {
    data: popularDestinations = [],
    isLoading: isLoadingPopularDestinations,
    isError: isPopularDestinationsError,
  } = useQuery<PopularDestination[]>({
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
    queryFn: async () => {
      const response = await fetch("/api/flights/popular-destinations");
      if (!response.ok) {
        throw new Error("Failed to fetch popular destinations");
      }
      return (await response.json()) as PopularDestination[];
    },
    queryKey: POPULAR_DESTINATIONS_QUERY_KEY,
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

  const handleSearch = form.handleSubmit((data) => {
    startTransition(async () => {
      setOptimisticSearching(true);
      setFormError(null);

      try {
        // Validate the data before submission using Zod native parsing
        const validationResult = flightSearchFormSchema.safeParse(data);

        if (!validationResult.success) {
          const errorMessage = validationResult.error.issues
            .map((issue) => {
              const field = issue.path.length > 0 ? `${issue.path.join(".")}: ` : "";
              return `${field}${issue.message}`;
            })
            .join(", ");
          setFormError(errorMessage);
          return;
        }

        // Type assertion is safe here since success=true guarantees data is present
        const validatedData = validationResult.data;
        await onSearch(validatedData);
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          { action: "handleSearch", context: "FlightSearchForm" }
        );
        setFormError(
          error instanceof Error ? error.message : "Search failed. Please try again."
        );
      } finally {
        setOptimisticSearching(false);
      }
    });
  });

  const handleSwapAirports = () => {
    const origin = form.getValues("origin");
    const destination = form.getValues("destination");

    form.setValue("origin", destination);
    form.setValue("destination", origin);
  };

  const handleQuickFill = (destination: { code: string; name: string }) => {
    form.setValue("destination", destination.code);
  };

  // Clear form error when form changes
  React.useEffect(() => {
    const subscription = form.watch(() => {
      if (formError) {
        setFormError(null);
      }
    });
    return () => subscription.unsubscribe();
  }, [form, formError]);

  return (
    <Card className={cn("w-full max-w-4xl mx-auto", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <Plane className="h-5 w-5 text-blue-600" />
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
                <Sparkles className="h-3 w-3 mr-1" />
                Smart Bundle: Save up to {smartBundles.total}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <Form {...form}>
          <form onSubmit={handleSearch} className="space-y-6">
            {/* Form Error Alert */}
            {formError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}

            {/* Trip Type Selector */}
            <FormField
              control={form.control}
              name="tripType"
              render={({ field }) => (
                <FormItem>
                  <div className="flex gap-2">
                    {(["round-trip", "one-way", "multi-city"] as const).map((type) => (
                      <Button
                        key={type}
                        type="button"
                        variant={field.value === type ? "default" : "outline"}
                        size="sm"
                        onClick={() => field.onChange(type)}
                        className="capitalize"
                      >
                        {type === "round-trip"
                          ? "Round Trip"
                          : type === "one-way"
                            ? "One Way"
                            : "Multi-City"}
                      </Button>
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Main Search Form */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              {/* From/To Section */}
              <div className="lg:col-span-6 grid grid-cols-1 md:grid-cols-2 gap-4 relative">
                <FormField
                  control={form.control}
                  name="origin"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">From</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
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

                {/* Swap Button */}
                <div className="hidden md:flex absolute left-1/2 top-8 transform -translate-x-1/2 z-10">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleSwapAirports}
                    className="rounded-full bg-background border-2 shadow-md hover:shadow-lg transition-shadow"
                  >
                    <ArrowRight className="h-4 w-4" />
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
                          <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
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

              {/* Dates Section */}
              <div className="lg:col-span-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="departureDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">Departure</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Calendar className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
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
                            <Calendar className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input type="date" className="pl-10" {...field} />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </div>

              {/* Passengers & Class */}
              <div className="lg:col-span-2 space-y-4">
                {/* Passengers */}
                <FormField
                  control={form.control}
                  name="passengers.adults"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">Adults</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Users className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
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

                {/* Children */}
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

                {/* Cabin Class */}
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
                            <SelectItem value="premium-economy">
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

            {/* Popular Destinations */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Popular destinations</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {isLoadingPopularDestinations
                  ? POPULAR_DESTINATION_SKELETON_KEYS.map((key) => (
                      <Button
                        key={`popular-destination-skeleton-${key}`}
                        variant="outline"
                        size="sm"
                        disabled
                        className="h-auto py-2 px-3 flex flex-col items-start animate-pulse"
                      >
                        <span className="font-medium text-muted-foreground">
                          Loading…
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Fetching deals
                        </span>
                      </Button>
                    ))
                  : destinationsToRender.map((dest) => (
                      <Button
                        key={dest.code}
                        variant="outline"
                        size="sm"
                        onClick={() => handleQuickFill(dest)}
                        className="h-auto py-2 px-3 flex flex-col items-start"
                      >
                        <span className="font-medium">{dest.name}</span>
                        <span className="text-xs text-green-600">
                          {dest.savings ? `Save ${dest.savings}` : "Popular now"}
                        </span>
                      </Button>
                    ))}
              </div>
              {isPopularDestinationsError && (
                <p className="text-xs text-muted-foreground">
                  Showing recent favorites while we refresh destination data.
                </p>
              )}
            </div>

            {/* Smart Bundle Preview */}
            {showSmartBundles && (
              <>
                <Separator />
                <div className="bg-linear-to-r from-blue-50 to-green-50 p-4 rounded-lg border">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-blue-600" />
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
            )}

            {/* Search Button */}
            <div className="flex gap-3 pt-2">
              <Button
                type="submit"
                disabled={isPending || optimisticSearching || !form.formState.isValid}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                size="lg"
              >
                {isPending || optimisticSearching ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Searching flights...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Search Flights
                  </>
                )}
              </Button>

              <Button variant="outline" size="lg" className="px-6" type="button">
                <Clock className="h-4 w-4 mr-2" />
                Flexible Dates
              </Button>
            </div>

            {/* Progress indicator for optimistic updates */}
            {(isPending || optimisticSearching) && (
              <div className="space-y-2">
                <Progress value={66} className="h-2" />
                <p className="text-xs text-muted-foreground text-center">
                  Searching 500+ airlines for the best deals...
                </p>
              </div>
            )}
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
