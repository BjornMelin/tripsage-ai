/**
 * @fileoverview Calendar page for managing Google Calendar integration.
 *
 * Provides UI for connecting Google Calendar, viewing events, creating events,
 * and exporting/importing ICS files.
 */

"use client";

import { useRouter } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { CalendarConnectionCard } from "@/components/calendar/calendar-connection-card";
import { CalendarEventForm } from "@/components/calendar/calendar-event-form";
import { CalendarEventList } from "@/components/calendar/calendar-event-list";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { DateUtils } from "@/lib/dates/unified-date-utils";

/**
 * Renders the calendar integration dashboard with connection status, events,
 * and creation workflow tabs.
 *
 * @returns Calendar management layout with tabbed controls.
 */
function CalendarEventListSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-48 mt-2" />
      </CardHeader>
      <CardContent className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-4 border rounded-lg space-y-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function CalendarPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("status");
  const { now, nextWeek } = useMemo(() => {
    const current = new Date();
    return {
      nextWeek: DateUtils.add(current, 7, "days"),
      now: current,
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Calendar</h2>
        <p className="text-muted-foreground">
          Manage your Google Calendar integration and events.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="status">Connection</TabsTrigger>
          <TabsTrigger value="events">Events</TabsTrigger>
          <TabsTrigger value="create">Create Event</TabsTrigger>
        </TabsList>

        <TabsContent value="status" className="space-y-6">
          <CalendarConnectionCard />
        </TabsContent>

        <TabsContent value="events" className="space-y-6">
          <Suspense fallback={<CalendarEventListSkeleton />}>
            <CalendarEventList timeMin={now} timeMax={nextWeek} />
          </Suspense>
        </TabsContent>

        <TabsContent value="create" className="space-y-6">
          <CalendarEventForm
            onSuccess={(_eventId) => {
              toast({
                description: "Your calendar event has been created successfully.",
                title: "Event created",
              });
              setActiveTab("events");
              router.refresh();
            }}
            onError={(error) => {
              console.error("Failed to create event:", error);
              toast({
                description: error,
                title: "Failed to create event",
                variant: "destructive",
              });
            }}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
