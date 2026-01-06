/**
 * @fileoverview Calendar page for managing Google Calendar integration.
 */

"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { CalendarConnectionCard } from "@/components/calendar/calendar-connection-card";
import { CalendarEventForm } from "@/components/calendar/calendar-event-form";
import { CalendarEventList } from "@/components/calendar/calendar-event-list";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { DateUtils } from "@/lib/dates/unified-date-utils";

/**
 * Renders the calendar integration dashboard with connection status, events,
 * and creation workflow tabs.
 *
 * @returns Calendar management layout with tabbed controls.
 */
export default function CalendarPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("status");
  const timeWindow = useMemo(() => {
    const start = DateUtils.startOf(new Date(), "day");
    return {
      nextWeek: DateUtils.add(start, 7, "days"),
      now: start,
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
          <CalendarEventList timeMin={timeWindow.now} timeMax={timeWindow.nextWeek} />
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
