/**
 * @fileoverview Calendar connection status component.
 *
 * Server Component that displays calendar connection status and list of
 * connected calendars.
 */

import { Calendar, CalendarCheck, CalendarX } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CalendarConnectClient } from "./calendar-connect-client";

/**
 * Props for CalendarStatus component.
 */
export interface CalendarStatusProps {
  /** Optional className for styling */
  className?: string;
}

/**
 * CalendarStatus component.
 *
 * Fetches calendar status from API and displays connection status and
 * list of calendars. Uses client component for OAuth connection action.
 */
export async function CalendarStatus({ className }: CalendarStatusProps) {
  // Fetch calendar status
  let statusData: {
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
  } | null = null;

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"}/api/calendar/status`,
      {
        cache: "no-store",
      }
    );
    if (response.ok) {
      statusData = await response.json();
    }
  } catch (error) {
    console.error("Failed to fetch calendar status:", error);
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
