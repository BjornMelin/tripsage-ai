"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
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
import type { ActivitySearchParams } from "@/types/search";

const activitySearchFormSchema = z.object({
  location: z.string().min(1, { message: "Location is required" }),
  startDate: z.string().min(1, { message: "Start date is required" }),
  endDate: z.string().min(1, { message: "End date is required" }),
  adults: z.number().min(1).max(20),
  children: z.number().min(0).max(10),
  infants: z.number().min(0).max(5),
  categories: z.array(z.string()),
  duration: z.number().min(1).max(48).optional(),
  priceMin: z.number().min(0).optional(),
  priceMax: z.number().min(0).optional(),
  rating: z.number().min(1).max(5).optional(),
});

type ActivitySearchFormValues = z.infer<typeof activitySearchFormSchema>;

interface ActivitySearchFormProps {
  onSearch?: (data: ActivitySearchParams) => void;
  initialValues?: Partial<ActivitySearchFormValues>;
}

const ACTIVITY_CATEGORIES = [
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
  const form = useForm<ActivitySearchFormValues>({
    resolver: zodResolver(activitySearchFormSchema),
    defaultValues: {
      location: "",
      startDate: "",
      endDate: "",
      adults: 1,
      children: 0,
      infants: 0,
      categories: [],
      ...initialValues,
    },
    mode: "onChange",
  });

  function onSubmit(data: ActivitySearchFormValues) {
    // Convert form data to search params
    const searchParams: ActivitySearchParams = {
      destination: data.location,
      date: data.startDate,
      adults: data.adults,
      children: data.children,
      infants: data.infants,
      category: data.categories?.[0], // Use first category as main category
      duration: data.duration
        ? {
            min: 0,
            max: data.duration,
          }
        : undefined,
    };

    console.log("Activity search params:", searchParams);

    if (onSearch) {
      onSearch(searchParams);
    }
  }

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
                          onChange={(e) =>
                            field.onChange(Number.parseInt(e.target.value, 10))
                          }
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
                          onChange={(e) =>
                            field.onChange(Number.parseInt(e.target.value, 10))
                          }
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
                          onChange={(e) =>
                            field.onChange(Number.parseInt(e.target.value, 10))
                          }
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
                      {ACTIVITY_CATEGORIES.map((category) => (
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
                          onChange={(e) =>
                            field.onChange(Number.parseInt(e.target.value, 10))
                          }
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
                          onChange={(e) =>
                            field.onChange(Number.parseFloat(e.target.value))
                          }
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
                          onChange={(e) =>
                            field.onChange(Number.parseInt(e.target.value, 10))
                          }
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
                          onChange={(e) =>
                            field.onChange(Number.parseInt(e.target.value, 10))
                          }
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
