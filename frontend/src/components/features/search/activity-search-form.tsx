/**
 * @fileoverview Activity search form component for searching activities.
 */
"use client";

import type { ActivitySearchParams } from "@schemas/search";
import { z } from "zod";
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

const ActivitySearchFormSchema = z.strictObject({
  adults: z
    .number()
    .int()
    .min(1, { error: "At least 1 adult required" })
    .max(20, { error: "Too many adults" }),
  categories: z.array(z.string()),
  children: z.number().int().min(0).max(10, { error: "Too many children" }),
  duration: z.number().int().min(1).max(48).optional(),
  endDate: z.string().min(1, { error: "End date is required" }),
  infants: z.number().int().min(0).max(5, { error: "Too many infants" }),
  location: z.string().min(1, { error: "Location is required" }),
  priceMax: z.number().min(0).optional(),
  priceMin: z.number().min(0).optional(),
  rating: z.number().min(1).max(5).optional(),
  startDate: z.string().min(1, { error: "Start date is required" }),
});

type ActivitySearchFormValues = z.infer<typeof ActivitySearchFormSchema>;

interface ActivitySearchFormProps {
  onSearch?: (data: ActivitySearchParams) => void;
  initialValues?: Partial<ActivitySearchFormValues>;
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
    ActivitySearchFormSchema,
    {
      adults: 1,
      categories: [],
      children: 0,
      endDate: "",
      infants: 0,
      location: "",
      startDate: "",
      ...initialValues,
    },
    {}
  );

  const onSubmit = (data: ActivitySearchFormValues) =>
    withClientTelemetrySpan(
      "search.activity.form.submit",
      { searchType: "activity" },
      async () => {
        const searchParams: ActivitySearchParams = {
          adults: data.adults,
          category: data.categories?.[0],
          children: data.children,
          date: data.startDate,
          destination: data.location,
          duration: data.duration
            ? {
                max: data.duration,
                min: 0,
              }
            : undefined,
          infants: data.infants,
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
                name="location"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Location</FormLabel>
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
                  name="startDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Start Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="endDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>End Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="adults"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Adults (18+)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          max={20}
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
                  name="children"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Children (3-17)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          max={10}
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
                  name="infants"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Infants (0-2)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          max={5}
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
                name="categories"
                render={() => (
                  <FormItem>
                    <FormLabel>Activity Categories</FormLabel>
                    <FormDescription>
                      Select the types of activities you're interested in
                    </FormDescription>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {ActivityCategories.map((category) => (
                        <label
                          key={category.id}
                          className="flex items-center space-x-2 border rounded-md p-2 cursor-pointer hover:bg-accent"
                        >
                          <input
                            type="checkbox"
                            value={category.id}
                            checked={form.watch("categories").includes(category.id)}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              const categories = form.getValues("categories");

                              if (checked) {
                                form.setValue("categories", [
                                  ...categories,
                                  category.id,
                                ]);
                              } else {
                                form.setValue(
                                  "categories",
                                  categories.filter((c) => c !== category.id)
                                );
                              }
                            }}
                            className="h-4 w-4"
                          />
                          <span className="text-sm">{category.label}</span>
                        </label>
                      ))}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <FormField
                  control={form.control}
                  name="duration"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Duration (hours)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          max={48}
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
                  name="rating"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Min Rating</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          max={5}
                          step={0.5}
                          placeholder="Any"
                          {...field}
                          value={field.value ?? ""}
                          onChange={(e) => {
                            const value = e.target.value;
                            field.onChange(
                              value === "" ? undefined : Number.parseFloat(value)
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
                  name="priceMin"
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
                  name="priceMax"
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
