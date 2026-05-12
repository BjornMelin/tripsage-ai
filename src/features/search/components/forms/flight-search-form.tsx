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
  type LucideIcon,
  MapPinIcon,
  PlaneIcon,
  SparklesIcon,
  UsersIcon,
} from "lucide-react";
import { useMemo } from "react";
import type { Control } from "react-hook-form";
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
import { dateInputValue } from "./common/date-input-value";

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
const TRIP_TYPE_OPTIONS = [
  { label: "Round Trip", value: "round-trip" },
  { label: "One Way", value: "one-way" },
  { label: "Multi-City", value: "multi-city" },
] as const satisfies readonly {
  label: string;
  value: FlightSearchFormData["tripType"];
}[];
const ADULT_COUNTS = [1, 2, 3, 4, 5, 6, 7, 8, 9] as const;
const CHILD_COUNTS = [0, 1, 2, 3, 4, 5, 6, 7, 8] as const;
const CABIN_CLASS_OPTIONS = [
  { label: "Economy", value: "economy" },
  { label: "Premium Economy", value: "premium_economy" },
  { label: "Business", value: "business" },
  { label: "First Class", value: "first" },
] as const satisfies readonly {
  label: string;
  value: FlightSearchFormData["cabinClass"];
}[];

type FlightFormControl = Control<FlightSearchFormValues>;
type IconInputFieldName = "origin" | "destination" | "departureDate" | "returnDate";

interface FlightSearchFormProps {
  onSearch: (params: FlightSearchParams) => Promise<void>;
  suggestions?: SearchSuggestion[];
  className?: string;
  showSmartBundles?: boolean;
  initialParams?: Partial<FlightSearchParams>;
}

function IconInputField({
  control,
  formatValue,
  icon: Icon,
  label,
  name,
  placeholder,
  type,
}: {
  control: FlightFormControl;
  formatValue?: (value: unknown) => string;
  icon: LucideIcon;
  label: string;
  name: IconInputFieldName;
  placeholder?: string;
  type?: "date";
}) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel className="text-sm font-medium">{label}</FormLabel>
          <div className="relative">
            <Icon
              aria-hidden="true"
              className="absolute left-3 top-3 h-4 w-4 text-muted-foreground"
            />
            <FormControl>
              <Input
                aria-label={label}
                placeholder={placeholder}
                type={type}
                className="pl-10"
                {...field}
                value={
                  formatValue
                    ? formatValue(field.value)
                    : typeof field.value === "string"
                      ? field.value
                      : ""
                }
              />
            </FormControl>
          </div>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function NumberSelectField({
  control,
  icon: Icon,
  label,
  name,
  plural,
  singular,
  values,
}: {
  control: FlightFormControl;
  icon?: LucideIcon;
  label: string;
  name: "passengers.adults" | "passengers.children";
  plural: string;
  singular: string;
  values: readonly number[];
}) {
  const select = (
    <SelectContent>
      {values.map((num) => (
        <SelectItem key={num} value={num.toString()}>
          {num} {num === 1 ? singular : plural}
        </SelectItem>
      ))}
    </SelectContent>
  );

  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel className="text-sm font-medium">{label}</FormLabel>
          <div className={Icon ? "relative" : undefined}>
            {Icon && (
              <Icon
                aria-hidden="true"
                className="absolute left-3 top-3 h-4 w-4 text-muted-foreground"
              />
            )}
            <Select
              value={field.value.toString()}
              onValueChange={(value) => field.onChange(Number.parseInt(value, 10))}
            >
              <FormControl>
                <SelectTrigger
                  aria-label={label}
                  className={Icon ? "pl-10" : undefined}
                >
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              {select}
            </Select>
          </div>
          <FormMessage />
        </FormItem>
      )}
    />
  );
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
            <div className="w-10 h-10 rounded-full bg-info/20 flex items-center justify-center">
              <PlaneIcon aria-hidden="true" className="h-5 w-5 text-info" />
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
                className="bg-success/10 text-success border-success/20"
              >
                <SparklesIcon aria-hidden="true" className="h-3 w-3 mr-1" />
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
              <ClockIcon aria-hidden="true" className="h-4 w-4 mr-2" />
              Flexible Dates
            </Button>
          }
          footer={
            showSmartBundles
              ? (_form, _state) => (
                  <>
                    <Separator />
                    <div className="bg-gradient-to-r from-info/10 to-success/10 p-4 rounded-lg border">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <SparklesIcon
                            aria-hidden="true"
                            className="h-5 w-5 text-info"
                          />
                          <h3 className="font-semibold text-sm">Smart Trip Bundle</h3>
                          <Badge
                            variant="secondary"
                            className="bg-success/20 text-success"
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
                          <div className="text-success font-semibold">
                            Save {smartBundles.hotel}
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="font-medium">+ Car Rental</div>
                          <div className="text-success font-semibold">
                            Save {smartBundles.car}
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="font-medium">Total Savings</div>
                          <div className="text-success font-semibold text-lg">
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
                    <fieldset>
                      <legend className="sr-only">Trip type</legend>
                      <div className="flex gap-2">
                        {TRIP_TYPE_OPTIONS.map(({ label, value }) => (
                          <Button
                            key={value}
                            type="button"
                            variant={field.value === value ? "default" : "outline"}
                            size="sm"
                            aria-pressed={field.value === value}
                            onClick={() => {
                              form.setValue("tripType", value, {
                                shouldDirty: true,
                                shouldTouch: true,
                                shouldValidate: true,
                              });
                            }}
                            className="capitalize"
                            disabled={state.isSubmitting}
                          >
                            {label}
                          </Button>
                        ))}
                      </div>
                    </fieldset>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                <div className="lg:col-span-6 grid grid-cols-1 md:grid-cols-2 gap-4 relative">
                  <IconInputField
                    control={form.control}
                    name="origin"
                    label="From"
                    icon={MapPinIcon}
                    placeholder="Departure city or airport…"
                  />

                  <div className="hidden md:flex absolute left-1/2 top-8 transform -translate-x-1/2 z-10">
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={handleSwapAirports}
                      disabled={state.isSubmitting}
                      className="rounded-full bg-background border-2 shadow-md hover:shadow-lg transition-shadow"
                      aria-label="Swap origin and destination"
                    >
                      <ArrowRightIcon aria-hidden="true" className="h-4 w-4" />
                    </Button>
                  </div>

                  <IconInputField
                    control={form.control}
                    name="destination"
                    label="To"
                    icon={MapPinIcon}
                    placeholder="Destination city or airport…"
                  />
                </div>

                <div className="lg:col-span-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <IconInputField
                    control={form.control}
                    name="departureDate"
                    label="Departure"
                    icon={CalendarIcon}
                    type="date"
                    formatValue={dateInputValue}
                  />

                  {isRoundTrip && (
                    <IconInputField
                      control={form.control}
                      name="returnDate"
                      label="Return"
                      icon={CalendarIcon}
                      type="date"
                      formatValue={dateInputValue}
                    />
                  )}
                </div>

                <div className="lg:col-span-2 space-y-4">
                  <NumberSelectField
                    control={form.control}
                    name="passengers.adults"
                    label="Adults"
                    icon={UsersIcon}
                    values={ADULT_COUNTS}
                    singular="Adult"
                    plural="Adults"
                  />

                  <NumberSelectField
                    control={form.control}
                    name="passengers.children"
                    label="Children (2-11)"
                    values={CHILD_COUNTS}
                    singular="Child"
                    plural="Children"
                  />

                  <FormField
                    control={form.control}
                    name="cabinClass"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">Class</FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger aria-label="Class">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {CABIN_CLASS_OPTIONS.map((option) => (
                              <SelectItem key={option.value} value={option.value}>
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
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
