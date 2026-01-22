/**
 * @fileoverview Activity search form component for searching activities.
 */

"use client";

import {
  type ActivitySearchFormData,
  type ActivitySearchParams,
  activitySearchFormSchema,
  activitySearchParamsSchema,
} from "@schemas/search";
import { useMemo } from "react";
import type { z } from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useSearchHistoryStore } from "@/features/search/store/search-history";
import { buildRecentQuickSelectItems } from "../common/recent-items";
import { type QuickSelectItem, SearchFormShell } from "../common/search-form-shell";
import { useSearchForm } from "../common/use-search-form";

type ActivitySearchFormValues = z.input<typeof activitySearchFormSchema>;

interface ActivitySearchFormProps {
  onSearch?: (data: ActivitySearchParams) => Promise<void>;
  initialValues?: Partial<ActivitySearchFormValues>;
}

export function ActivitySearchForm({
  onSearch,
  initialValues,
}: ActivitySearchFormProps) {
  const { participants: initialParticipants, ...restInitialValues } =
    initialValues ?? {};

  const form = useSearchForm(
    activitySearchFormSchema,
    {
      category: "",
      date: "",
      dateRange: {
        end: "",
        start: "",
      },
      destination: "",
      difficulty: undefined,
      duration: {
        max: undefined,
        min: undefined,
      },
      indoor: undefined,
      participants: {
        adults: 1,
        children: 0,
        infants: 0,
        ...initialParticipants,
      },
      priceRange: {
        max: undefined,
        min: undefined,
      },
      ...restInitialValues,
    },
    {}
  );

  const recentSearchesByType = useSearchHistoryStore(
    (state) => state.recentSearchesByType.activity
  );
  const recentSearches = useMemo(
    () => recentSearchesByType.slice(0, 4),
    [recentSearchesByType]
  );
  const recentItems: QuickSelectItem<ActivitySearchFormValues>[] = useMemo(() => {
    return buildRecentQuickSelectItems<ActivitySearchFormValues, ActivitySearchParams>(
      recentSearches,
      activitySearchParamsSchema,
      (params, search) => {
        const destination = params.destination ?? "Destination";

        const label = params.category
          ? `${destination} · ${params.category}`
          : destination;
        const description = params.date ?? undefined;

        const item: QuickSelectItem<ActivitySearchFormValues> = {
          id: search.id,
          label,
          params: {
            category: params.category ?? "",
            date: params.date ?? "",
            dateRange: params.dateRange
              ? {
                  end: params.dateRange.end ?? "",
                  start: params.dateRange.start ?? "",
                }
              : undefined,
            destination: params.destination ?? "",
            difficulty: params.difficulty ?? undefined,
            duration: params.duration ?? undefined,
            indoor: params.indoor ?? undefined,
            participants: {
              adults: params.adults ?? 1,
              children: params.children ?? 0,
              infants: params.infants ?? 0,
            },
            priceRange: params.priceRange ?? undefined,
          },
          ...(description ? { description } : {}),
        };

        return item;
      }
    );
  }, [recentSearches]);

  const handleSubmit = async (data: ActivitySearchFormData) => {
    const searchParams: ActivitySearchParams = {
      adults: data.participants.adults,
      category: data.category,
      children: data.participants.children,
      date: data.date,
      dateRange: data.dateRange,
      destination: data.destination,
      difficulty: data.difficulty,
      duration: data.duration,
      indoor: data.indoor,
      infants: data.participants.infants,
      priceRange: data.priceRange,
    };

    if (onSearch) {
      await onSearch(searchParams);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity Search</CardTitle>
        <CardDescription>
          Discover exciting activities and experiences at your destination
        </CardDescription>
      </CardHeader>
      <CardContent>
        <SearchFormShell
          form={form}
          onSubmit={handleSubmit}
          telemetrySpanName="search.activity.form.submit"
          telemetryAttributes={{ searchType: "activity" }}
          telemetryErrorMetadata={{
            action: "submit",
            context: "ActivitySearchForm",
          }}
          submitLabel="Search Activities"
          loadingLabel="Searching activities…"
          recentItems={recentItems}
          recentLabel="Recent searches"
        >
          {(form) => (
            <div className="space-y-6">
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="destination"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Destination</FormLabel>
                      <FormControl>
                        <Input placeholder="City, region, or destination…" {...field} />
                      </FormControl>
                      <FormDescription>
                        Enter city name, region, or specific destination
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <FormField
                    control={form.control}
                    name="date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Date</FormLabel>
                        <FormControl>
                          <Input type="date" {...field} value={field.value ?? ""} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="dateRange.start"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Start Date (Range)</FormLabel>
                        <FormControl>
                          <Input type="date" {...field} value={field.value ?? ""} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="dateRange.end"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>End Date (Range)</FormLabel>
                        <FormControl>
                          <Input type="date" {...field} value={field.value ?? ""} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <FormField
                    control={form.control}
                    name="participants.adults"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Adults (18+)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            max={50}
                            {...field}
                            value={field.value ?? 1}
                            onChange={(e) => {
                              const value = e.target.value;
                              const parsed = Number.parseInt(value, 10);
                              field.onChange(
                                value === "" || Number.isNaN(parsed) ? 1 : parsed
                              );
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="participants.children"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Children (3-17)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={0}
                            max={50}
                            {...field}
                            value={field.value ?? 0}
                            onChange={(e) => {
                              const value = e.target.value;
                              const parsed = Number.parseInt(value, 10);
                              field.onChange(
                                value === "" || Number.isNaN(parsed) ? 0 : parsed
                              );
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="participants.infants"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Infants (0-2)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={0}
                            max={50}
                            {...field}
                            value={field.value ?? 0}
                            onChange={(e) => {
                              const value = e.target.value;
                              const parsed = Number.parseInt(value, 10);
                              field.onChange(
                                value === "" || Number.isNaN(parsed) ? 0 : parsed
                              );
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Activity Category</FormLabel>
                      <FormDescription>
                        Select the type of activity you're interested in
                      </FormDescription>
                      <FormControl>
                        <Input placeholder="e.g. outdoor, cultural, food" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <FormField
                    control={form.control}
                    name="duration.min"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Min Duration (hours)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            placeholder="Any"
                            {...field}
                            value={field.value ?? ""}
                            onChange={(e) => {
                              const value = e.target.value;
                              field.onChange(
                                value === "" ? undefined : Number.parseInt(value, 10)
                              );
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="duration.max"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Max Duration (hours)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            placeholder="Any"
                            {...field}
                            value={field.value ?? ""}
                            onChange={(e) => {
                              const value = e.target.value;
                              field.onChange(
                                value === "" ? undefined : Number.parseInt(value, 10)
                              );
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="priceRange.min"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Min Price ($)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={0}
                            placeholder="No minimum"
                            {...field}
                            value={field.value ?? ""}
                            onChange={(e) => {
                              const value = e.target.value;
                              field.onChange(
                                value === "" ? undefined : Number.parseInt(value, 10)
                              );
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="priceRange.max"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Max Price ($)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={0}
                            placeholder="No maximum"
                            {...field}
                            value={field.value ?? ""}
                            onChange={(e) => {
                              const value = e.target.value;
                              field.onChange(
                                value === "" ? undefined : Number.parseInt(value, 10)
                              );
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            </div>
          )}
        </SearchFormShell>
      </CardContent>
    </Card>
  );
}
