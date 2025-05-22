"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import type { FlightSearchParams } from "@/types/search";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const flightSearchFormSchema = z.object({
  tripType: z.enum(["oneWay", "roundTrip", "multiCity"]),
  origin: z.string().min(3, { message: "Origin is required" }),
  destination: z.string().min(3, { message: "Destination is required" }),
  departureDate: z.string().min(1, { message: "Departure date is required" }),
  returnDate: z.string().optional(),
  adults: z.number().min(1).max(9).default(1),
  children: z.number().min(0).max(9).default(0),
  infants: z.number().min(0).max(9).default(0),
  cabinClass: z.enum(["economy", "premium_economy", "business", "first"]).default("economy"),
  directOnly: z.boolean().default(false),
  flexibleDates: z.boolean().default(false),
});

type FlightSearchFormValues = z.infer<typeof flightSearchFormSchema>;

interface FlightSearchFormProps {
  onSearch?: (data: FlightSearchParams) => void;
  initialValues?: Partial<FlightSearchFormValues>;
}

export function FlightSearchForm({ 
  onSearch,
  initialValues = {
    tripType: "roundTrip",
    adults: 1,
    children: 0,
    infants: 0,
    cabinClass: "economy",
    directOnly: false,
    flexibleDates: false,
  }
}: FlightSearchFormProps) {
  const [tripType, setTripType] = useState<"oneWay" | "roundTrip" | "multiCity">(initialValues.tripType || "roundTrip");

  const form = useForm<FlightSearchFormValues>({
    resolver: zodResolver(flightSearchFormSchema),
    defaultValues: initialValues,
    mode: "onChange",
  });

  function onSubmit(data: FlightSearchFormValues) {
    // Convert form data to search params
    const searchParams: FlightSearchParams = {
      origin: data.origin,
      destination: data.destination,
      startDate: data.departureDate,
      endDate: data.returnDate || data.departureDate,
      adults: data.adults,
      children: data.children,
      infants: data.infants,
      cabinClass: data.cabinClass,
      directOnly: data.directOnly,
    };

    console.log("Search params:", searchParams);
    
    if (onSearch) {
      onSearch(searchParams);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Flight Search</CardTitle>
        <CardDescription>
          Search for flights to any destination
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="space-y-4">
              <Tabs 
                value={tripType} 
                onValueChange={(value) => {
                  setTripType(value as "oneWay" | "roundTrip" | "multiCity");
                  form.setValue("tripType", value as "oneWay" | "roundTrip" | "multiCity");
                }}
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="roundTrip">Round Trip</TabsTrigger>
                  <TabsTrigger value="oneWay">One Way</TabsTrigger>
                  <TabsTrigger value="multiCity">Multi-City</TabsTrigger>
                </TabsList>
              </Tabs>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="origin"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Origin</FormLabel>
                      <FormControl>
                        <Input placeholder="City or airport" {...field} />
                      </FormControl>
                      <FormDescription>
                        Enter city name or airport code
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="destination"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Destination</FormLabel>
                      <FormControl>
                        <Input placeholder="City or airport" {...field} />
                      </FormControl>
                      <FormDescription>
                        Enter city name or airport code
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="departureDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Departure Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {tripType === "roundTrip" && (
                  <FormField
                    control={form.control}
                    name="returnDate"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Return Date</FormLabel>
                        <FormControl>
                          <Input type="date" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="adults"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Adults</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={1} 
                          max={9} 
                          {...field} 
                          onChange={(e) => field.onChange(Number.parseInt(e.target.value))}
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
                      <FormLabel>Children (2-11)</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={0} 
                          max={9} 
                          {...field} 
                          onChange={(e) => field.onChange(Number.parseInt(e.target.value))}
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
                      <FormLabel>Infants (0-1)</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={0} 
                          max={9} 
                          {...field} 
                          onChange={(e) => field.onChange(Number.parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="cabinClass"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cabin Class</FormLabel>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      <Button
                        type="button"
                        variant={field.value === "economy" ? "default" : "outline"}
                        onClick={() => form.setValue("cabinClass", "economy")}
                        className="w-full"
                      >
                        Economy
                      </Button>
                      <Button
                        type="button"
                        variant={field.value === "premium_economy" ? "default" : "outline"}
                        onClick={() => form.setValue("cabinClass", "premium_economy")}
                        className="w-full"
                      >
                        Premium Economy
                      </Button>
                      <Button
                        type="button"
                        variant={field.value === "business" ? "default" : "outline"}
                        onClick={() => form.setValue("cabinClass", "business")}
                        className="w-full"
                      >
                        Business
                      </Button>
                      <Button
                        type="button"
                        variant={field.value === "first" ? "default" : "outline"}
                        onClick={() => form.setValue("cabinClass", "first")}
                        className="w-full"
                      >
                        First
                      </Button>
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="directOnly"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
                      <div className="space-y-0.5">
                        <FormLabel>Direct Flights Only</FormLabel>
                        <FormDescription>
                          Search for non-stop flights only
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="flexibleDates"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
                      <div className="space-y-0.5">
                        <FormLabel>Flexible Dates</FormLabel>
                        <FormDescription>
                          Show flights 3 days before and after
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <Button type="submit" className="w-full">Search Flights</Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}