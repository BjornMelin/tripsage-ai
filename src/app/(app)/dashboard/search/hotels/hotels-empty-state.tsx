/**
 * @fileoverview Empty-state UI for the HotelsSearchClient.
 */

"use client";

import { Building2Icon, LightbulbIcon, MapPinIcon, StarIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { PopularDestinationProps } from "./popular-destinations";

type HotelsEmptyStateProps = {
  baseCurrency: string;
  popularDestinations: PopularDestinationProps[];
  isPopularDestinationsLoading: boolean;
};

const ACCOMMODATION_TIPS = [
  {
    description:
      "While we show you the best deals from all sites, booking directly with hotels can sometimes get you perks like free breakfast, room upgrades, or loyalty points.",
    title: "Book directly with hotels for possible benefits",
  },
  {
    description:
      "A slightly higher price for a central location can save you time and transportation costs. Use the map view to see where properties are located relative to attractions.",
    title: "Consider location carefully",
  },
  {
    description:
      "For maximum flexibility, filter for properties with free cancellation. This allows you to lock in a good rate while still keeping your options open.",
    title: "Check cancellation policies",
  },
  {
    description:
      "Look at reviews from the last 3–6 months to get the most accurate picture of the current state of the property. Pay special attention to reviews from travelers similar to you.",
    title: "Read recent reviews",
  },
] as const;

export function HotelsEmptyState({
  baseCurrency,
  popularDestinations,
  isPopularDestinationsLoading,
}: HotelsEmptyStateProps) {
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPinIcon className="h-5 w-5" />
            Popular Destinations
          </CardTitle>
          <CardDescription>Trending hotel destinations and deals</CardDescription>
        </CardHeader>
        <CardContent>
          {isPopularDestinationsLoading ? (
            <p className="text-sm text-muted-foreground mb-4">
              Loading popular destinations…
            </p>
          ) : null}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {popularDestinations.map((destination) => (
              <PopularDestinationCard
                key={destination.destination}
                currencyCode={baseCurrency}
                {...destination}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LightbulbIcon className="h-5 w-5" />
            Accommodation Tips
          </CardTitle>
          <CardDescription>
            General tips to help you find great accommodations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {ACCOMMODATION_TIPS.map((tip, index) => (
              <div key={tip.title}>
                <AccommodationTip title={tip.title} description={tip.description} />
                {index < ACCOMMODATION_TIPS.length - 1 ? <Separator /> : null}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

type PopularDestinationCardProps = PopularDestinationProps & {
  currencyCode: string;
};

function PopularDestinationCard({
  destination,
  currencyCode,
  priceFrom,
  rating,
}: PopularDestinationCardProps) {
  const formattedPrice = new Intl.NumberFormat(undefined, {
    currency: currencyCode,
    maximumFractionDigits: 0,
    style: "currency",
  }).format(priceFrom);

  return (
    <Card className="h-full overflow-hidden transition-colors hover:bg-accent/50 group">
      <div className="h-40 bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center relative">
        <Building2Icon className="h-16 w-16 text-primary/30" />
        <div className="absolute top-3 right-3">
          <Badge variant="secondary" className="text-xs flex items-center gap-1">
            <StarIcon className="h-3 w-3 fill-yellow-400 text-yellow-400" />
            {rating}
          </Badge>
        </div>
      </div>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="font-medium group-hover:text-primary transition-colors">
              {destination}
            </h3>
            <p className="text-xs text-muted-foreground mt-1">Hotels & Resorts</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">from</p>
            <span className="font-semibold text-lg">{formattedPrice}</span>
            <p className="text-xs text-muted-foreground">per night</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

type AccommodationTipProps = {
  title: string;
  description: string;
};

function AccommodationTip({ title, description }: AccommodationTipProps) {
  return (
    <div className="flex gap-4">
      <div className="shrink-0">
        <div className="rounded-full bg-primary/10 p-2">
          <LightbulbIcon className="h-4 w-4 text-primary" />
        </div>
      </div>
      <div>
        <h3 className="font-medium mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
