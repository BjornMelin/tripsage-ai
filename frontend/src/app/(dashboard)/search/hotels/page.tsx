import { SearchLayout } from "@/components/layouts/search-layout";
import { HotelSearchForm } from "@/components/features/search/hotel-search-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function HotelSearchPage() {
  return (
    <SearchLayout>
      <div className="grid gap-6">
        <HotelSearchForm />

        <Card>
          <CardHeader>
            <CardTitle>Popular Destinations</CardTitle>
            <CardDescription>
              Trending hotel destinations and deals
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <PopularDestinationCard
                destination="New York"
                priceFrom={199}
                image="/placeholder.jpg"
                rating={4.8}
              />
              <PopularDestinationCard
                destination="Paris"
                priceFrom={229}
                image="/placeholder.jpg"
                rating={4.7}
              />
              <PopularDestinationCard
                destination="Tokyo"
                priceFrom={179}
                image="/placeholder.jpg"
                rating={4.9}
              />
              <PopularDestinationCard
                destination="London"
                priceFrom={249}
                image="/placeholder.jpg"
                rating={4.6}
              />
              <PopularDestinationCard
                destination="Barcelona"
                priceFrom={159}
                image="/placeholder.jpg"
                rating={4.5}
              />
              <PopularDestinationCard
                destination="Rome"
                priceFrom={169}
                image="/placeholder.jpg"
                rating={4.7}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Accommodation Tips</CardTitle>
            <CardDescription>
              Tips to help you find the best accommodations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <AccommodationTip
                title="Book directly with hotels for possible benefits"
                description="While we show you the best deals from all sites, booking directly with hotels can sometimes get you perks like free breakfast, room upgrades, or loyalty points."
              />
              <AccommodationTip
                title="Consider location carefully"
                description="A slightly higher price for a central location can save you time and transportation costs. Use the map view to see where properties are located relative to attractions."
              />
              <AccommodationTip
                title="Check cancellation policies"
                description="For maximum flexibility, filter for properties with free cancellation. This allows you to lock in a good rate while still keeping your options open."
              />
              <AccommodationTip
                title="Read recent reviews"
                description="Look at reviews from the last 3-6 months to get the most accurate picture of the current state of the property. Pay special attention to reviews from travelers similar to you."
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </SearchLayout>
  );
}

function PopularDestinationCard({
  destination,
  priceFrom,
  image,
  rating,
}: {
  destination: string;
  priceFrom: number;
  image: string;
  rating: number;
}) {
  return (
    <Card className="h-full overflow-hidden hover:bg-accent/50 transition-colors cursor-pointer">
      <div className="h-40 bg-muted flex items-center justify-center">
        <span className="text-muted-foreground">Image Placeholder</span>
      </div>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="font-medium">{destination}</h3>
            <div className="flex items-center mt-1">
              <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full">
                {rating} ★
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">from</p>
            <span className="font-semibold">${priceFrom}</span>
            <p className="text-xs text-muted-foreground">per night</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AccommodationTip({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="p-4 border rounded-lg">
      <h3 className="font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
