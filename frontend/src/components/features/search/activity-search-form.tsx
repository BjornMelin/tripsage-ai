/**
 * @fileoverview Activity search form component for searching activities.
 */

"use client";

import {
  activitySearchFormSchema,
  type ActivitySearchFormData,
  type ActivitySearchParams,
} from "@schemas/search";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { withClientTelemetrySpan } from "@/lib/telemetry/client";
import { useSearchForm } from "./common/use-search-form";

interface ActivitySearchFormProps {
  onSearch?: (data: ActivitySearchParams) => void;
  initialValues?: Partial<ActivitySearchFormData>;
}

const ActivityCategories = [
  { id: "outdoor", label: "Outdoor & Adventure" },
  { id: "cultural", label: "Cultural & Historical" },
  { id: "food", label: "Food & Drink" },
  { id: "tours", label: "Guided Tours" },
  { id: "water", label: "Water Sports" },
  { id: "wildlife", label: "Wildlife & Nature" },
  { id: "sports", label: "Sports & Recreation" },
  { id: "nightlife", label: "Nightlife & Entertainment" },
  { id: "wellness", label: "Wellness & Spa" },
  { id: "shopping", label: "Shopping" },
  { id: "transportation", label: "Transportation" },
  { id: "classes", label: "Classes & Workshops" },
];

export function ActivitySearchForm({
  onSearch,
  initialValues,
}: ActivitySearchFormProps) {
  const form = useSearchForm(
    activitySearchFormSchema,
    {
      destination: "",
      participants: {
        adults: 1,
        children: 0,
      },
      ...initialValues,
    },
    {}
  );

  const onSubmit = (data: ActivitySearchFormData) =>
    withClientTelemetrySpan(
      "search.activity.form.submit",
      { searchType: "activity" },
      async () => {
        const searchParams: ActivitySearchParams = {
          adults: data.participants.adults,
          children: data.participants.children,
          date: data.date,
          destination: data.destination,
          category: data.category,
          difficulty: data.difficulty,
          duration: data.duration,
          indoor: data.indoor,
        };

        if (onSearch) {
          await onSearch(searchParams);
        }
      }
    );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity Search</CardTitle>
        <CardDescription>
          Discover exciting activities and experiences at your destination
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="destination"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Destination</FormLabel>
                    <FormControl>
                      <Input placeholder="City, region, or destination" {...field} />
                    </FormControl>
                    <FormDescription>
                      Enter city name, region, or specific destination
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
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
                        <Input type="date" {...field} />
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
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

            <Button type="submit" className="w-full">
              Search Activities
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
