/**
 * @fileoverview Calendar connection status card component.
 *
 * Client component that fetches calendar status via API route to avoid
 * server/client boundary violations. Displays connection status and list
 * of connected calendars.
 */

"use client";

import { Calendar, CalendarCheck, CalendarX } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { CalendarConnectClient } from "./calendar-connect-client";

/**
 * Props for CalendarConnectionCard component.
 */
export interface CalendarConnectionCardProps {
  /** Optional className for styling */
  className?: string;
}

/**
 * CalendarConnectionCard component.
 *
 * Client component that fetches calendar status via API and renders
 * the connection status UI.
 */
export function CalendarConnectionCard({ className }: CalendarConnectionCardProps) {
  const [statusData, setStatusData] = useState<{
    connected: boolean;
    calendars?: Array<{
      id: string;
      summary: string;
      description?: string;
      timeZone?: string;
      primary?: boolean;
      accessRole?: string;
    }>;
    message?: string;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCalendarStatus = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetch("/api/calendar/status", {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`Failed to fetch calendar status: ${response.statusText}`);
        }
        const data = await response.json();
        setStatusData(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        recordClientErrorOnActiveSpan(err instanceof Error ? err : new Error(message), {
          action: "loadCalendarStatus",
          context: "CalendarConnectionCard",
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadCalendarStatus();
  }, []);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">Loading calendar status...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <p className="text-sm text-destructive">Error: {error}</p>
        </CardContent>
      </Card>
    );
  }

  const isConnected = statusData?.connected ?? false;
  const calendars = statusData?.calendars ?? [];

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {isConnected ? (
            <>
              <CalendarCheck className="h-5 w-5 text-green-600" />
              Calendar Connected
            </>
          ) : (
            <>
              <CalendarX className="h-5 w-5 text-muted-foreground" />
              Calendar Not Connected
            </>
          )}
        </CardTitle>
        <CardDescription>
          {isConnected
            ? "Your Google Calendar is connected and ready to use."
            : "Connect your Google Calendar to sync events and check availability."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isConnected ? (
          <div className="space-y-4">
            {calendars.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-2">Connected Calendars</h3>
                <ul className="space-y-2">
                  {calendars.map((cal) => (
                    <li
                      key={cal.id}
                      className="flex items-center justify-between p-2 border rounded"
                    >
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">{cal.summary}</p>
                          {cal.description && (
                            <p className="text-xs text-muted-foreground">
                              {cal.description}
                            </p>
                          )}
                          {cal.primary && (
                            <span className="text-xs text-blue-600">Primary</span>
                          )}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <CalendarConnectClient />
        )}
      </CardContent>
    </Card>
  );
}
