"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { AccommodationSearchParams } from "@/types/search";

const hotelSearchFormSchema = z.object({
  location: z.string().min(1, { message: "Location is required" }),
  checkIn: z.string().min(1, { message: "Check-in date is required" }),
  checkOut: z.string().min(1, { message: "Check-out date is required" }),
  rooms: z.number().min(1).max(9).default(1),
  adults: z.number().min(1).max(9).default(1),
  children: z.number().min(0).max(9).default(0),
  rating: z.number().min(1).max(5).optional(),
  priceMin: z.number().min(0).optional(),
  priceMax: z.number().min(0).optional(),
  amenities: z.array(z.string()).default([]),
});

type HotelSearchFormValues = z.infer<typeof hotelSearchFormSchema>;

interface HotelSearchFormProps {
  onSearch?: (data: AccommodationSearchParams) => void;
  initialValues?: Partial<HotelSearchFormValues>;
}

const AMENITIES = [
  { id: "wifi", label: "Free WiFi" },
  { id: "breakfast", label: "Free Breakfast" },
  { id: "parking", label: "Free Parking" },
  { id: "pool", label: "Swimming Pool" },
  { id: "gym", label: "Fitness Center" },
  { id: "restaurant", label: "Restaurant" },
  { id: "spa", label: "Spa" },
  { id: "aircon", label: "Air Conditioning" },
];

export function HotelSearchForm({ 
  onSearch,
  initialValues = {
    rooms: 1,
    adults: 1,
    children: 0,
    amenities: [],
  }
}: HotelSearchFormProps) {
  const form = useForm<HotelSearchFormValues>({
    resolver: zodResolver(hotelSearchFormSchema),
    defaultValues: initialValues,
    mode: "onChange",
  });

  function onSubmit(data: HotelSearchFormValues) {
    // Convert form data to search params
    const searchParams: AccommodationSearchParams = {
      destination: data.location,
      startDate: data.checkIn,
      endDate: data.checkOut,
      adults: data.adults,
      children: data.children,
      infants: 0,
      rooms: data.rooms,
      amenities: data.amenities,
      rating: data.rating,
      priceRange: (data.priceMin || data.priceMax) ? {
        min: data.priceMin || 0,
        max: data.priceMax || 10000,
      } : undefined,
    };

    console.log("Search params:", searchParams);
    
    if (onSearch) {
      onSearch(searchParams);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hotel Search</CardTitle>
        <CardDescription>
          Find the perfect accommodation for your stay
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
                      <Input placeholder="City, address, or landmark" {...field} />
                    </FormControl>
                    <FormDescription>
                      Enter city name, specific address, or landmark
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="checkIn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Check-in Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="checkOut"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Check-out Date</FormLabel>
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
                  name="rooms"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Rooms</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={1} 
                          max={9} 
                          {...field} 
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

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
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
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
                      <FormLabel>Children (0-17)</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={0} 
                          max={9} 
                          {...field} 
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="rating"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Star Rating (min)</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={1} 
                          max={5} 
                          {...field} 
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
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
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
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
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="amenities"
                render={() => (
                  <FormItem>
                    <FormLabel>Amenities</FormLabel>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {AMENITIES.map((amenity) => (
                        <label key={amenity.id} className="flex items-center space-x-2 border rounded-md p-2 cursor-pointer hover:bg-accent">
                          <input
                            type="checkbox"
                            value={amenity.id}
                            checked={form.watch("amenities").includes(amenity.id)}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              const amenities = form.getValues("amenities");
                              
                              if (checked) {
                                form.setValue("amenities", [...amenities, amenity.id]);
                              } else {
                                form.setValue(
                                  "amenities",
                                  amenities.filter((a) => a !== amenity.id)
                                );
                              }
                            }}
                            className="h-4 w-4"
                          />
                          <span>{amenity.label}</span>
                        </label>
                      ))}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Button type="submit" className="w-full">Search Hotels</Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}