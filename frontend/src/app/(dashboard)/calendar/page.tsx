/**
 * @fileoverview Calendar page for managing Google Calendar integration.
 *
 * Provides UI for connecting Google Calendar, viewing events, creating events,
 * and exporting/importing ICS files.
 */

"use client";

import { useRouter } from "next/navigation";
import { Suspense, useState } from "react";
import { CalendarConnect } from "@/components/calendar/calendar-connect";
import { CalendarEventForm } from "@/components/calendar/calendar-event-form";
import { CalendarEventList } from "@/components/calendar/calendar-event-list";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function CalendarSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

export default function CalendarPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("status");
  const now = new Date();
  const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Calendar</h2>
        <p className="text-muted-foreground">
          Manage your Google Calendar integration and events.
        </p>
      </div>

      <Suspense fallback={<CalendarSkeleton />}>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList>
            <TabsTrigger value="status">Connection</TabsTrigger>
            <TabsTrigger value="events">Events</TabsTrigger>
            <TabsTrigger value="create">Create Event</TabsTrigger>
          </TabsList>

          <TabsContent value="status" className="space-y-6">
            <CalendarConnect />
          </TabsContent>

          <TabsContent value="events" className="space-y-6">
            <CalendarEventList timeMin={now} timeMax={nextWeek} />
          </TabsContent>

          <TabsContent value="create" className="space-y-6">
            <CalendarEventForm
              onSuccess={(_eventId) => {
                // Switch to events tab and refresh
                setActiveTab("events");
                router.refresh();
              }}
              onError={(error) => {
                console.error("Failed to create event:", error);
                alert(`Failed to create event: ${error}`);
              }}
            />
          </TabsContent>
        </Tabs>
      </Suspense>
    </div>
  );
}
