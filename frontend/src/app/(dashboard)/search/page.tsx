import { SearchLayout } from "@/components/layouts/search-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function SearchPage() {
  return (
    <SearchLayout>
      <div className="grid gap-6">
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Search Options</CardTitle>
            <CardDescription>
              Start your search for flights, hotels, activities or destinations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="all" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="flights">Flights</TabsTrigger>
                <TabsTrigger value="hotels">Hotels</TabsTrigger>
                <TabsTrigger value="activities">Activities</TabsTrigger>
              </TabsList>
              <TabsContent value="all" className="py-4">
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <SearchQuickOptionCard 
                    title="Find Flights" 
                    description="Search for flights to any destination"
                    href="/dashboard/search/flights"
                  />
                  <SearchQuickOptionCard 
                    title="Book Hotels" 
                    description="Find accommodations for your stay"
                    href="/dashboard/search/hotels"
                  />
                  <SearchQuickOptionCard 
                    title="Discover Activities" 
                    description="Explore things to do at your destination"
                    href="/dashboard/search/activities"
                  />
                  <SearchQuickOptionCard 
                    title="Browse Destinations" 
                    description="Get inspired for your next trip"
                    href="/dashboard/search/destinations"
                  />
                </div>
              </TabsContent>
              <TabsContent value="flights" className="py-4">
                <p>Redirecting to flights search...</p>
              </TabsContent>
              <TabsContent value="hotels" className="py-4">
                <p>Redirecting to hotels search...</p>
              </TabsContent>
              <TabsContent value="activities" className="py-4">
                <p>Redirecting to activities search...</p>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <Card className="w-full">
          <CardHeader>
            <CardTitle>Recent Searches</CardTitle>
            <CardDescription>
              Your most recent search queries
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <RecentSearchCard 
                title="New York to London" 
                type="Flight"
                date="May 26, 2025"
              />
              <RecentSearchCard 
                title="Hotels in Barcelona" 
                type="Hotel"
                date="May 22, 2025"
              />
              <RecentSearchCard 
                title="Activities in Tokyo" 
                type="Activity"
                date="May 18, 2025"
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </SearchLayout>
  );
}

function SearchQuickOptionCard({ 
  title, 
  description, 
  href 
}: { 
  title: string;
  description: string;
  href: string;
}) {
  return (
    <a href={href} className="block">
      <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{description}</p>
        </CardContent>
      </Card>
    </a>
  );
}

function RecentSearchCard({ 
  title, 
  type, 
  date 
}: { 
  title: string;
  type: string;
  date: string;
}) {
  return (
    <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-base">{title}</CardTitle>
          <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full">
            {type}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between items-center">
          <p className="text-xs text-muted-foreground">{date}</p>
          <button className="text-xs text-primary">Search again</button>
        </div>
      </CardContent>
    </Card>
  );
}