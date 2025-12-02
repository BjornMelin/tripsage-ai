/**
 * @fileoverview Calendar connection status card component.
 *
 * Client component that fetches calendar status via API route to avoid
 * server/client boundary violations. Displays connection status and list
 * of connected calendars.
 */

"use client";

import type { CalendarStatusResponse } from "@schemas/calendar";
import {
  AlertCircleIcon,
  CalendarCheckIcon,
  CalendarIcon,
  CalendarXIcon,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
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
  const [statusData, setStatusData] = useState<CalendarStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const loadCalendarStatus = useCallback(async () => {
    // Cancel any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      setIsLoading(true);
      setError(null);
      const response = await fetch("/api/calendar/status", {
        cache: "no-store",
        signal: abortController.signal,
      });
      if (!response.ok) {
        // Try to parse JSON error body, fallback to statusText
        let errorMessage =
          response.statusText || `Failed to fetch calendar status (${response.status})`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorData.message || errorMessage;
        } catch {
          // Not JSON, use statusText
        }
        throw new Error(errorMessage);
      }
      const data = await response.json();
      // Only update state if request wasn't aborted
      if (!abortController.signal.aborted) {
        setStatusData(data);
      }
    } catch (err) {
      // Don't update state if request was aborted
      if (abortController.signal.aborted) {
        return;
      }
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      try {
        recordClientErrorOnActiveSpan(err instanceof Error ? err : new Error(message), {
          action: "loadCalendarStatus",
          context: "CalendarConnectionCard",
        });
      } catch (telemetryError) {
        // Swallow telemetry errors to avoid breaking component
        if (process.env.NODE_ENV === "development") {
          console.error("Failed to record telemetry error:", telemetryError);
        }
      }
    } finally {
      if (!abortController.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    loadCalendarStatus();
    return () => {
      // Cleanup: abort any pending request on unmount
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadCalendarStatus]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-6 w-48" />
          </CardTitle>
          <CardDescription>
            <Skeleton className="h-4 w-64" />
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <Alert variant="destructive">
            <AlertCircleIcon className="h-4 w-4" />
            <AlertTitle>Failed to load calendar status</AlertTitle>
            <AlertDescription className="mt-2">{error}</AlertDescription>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => {
                setIsLoading(true);
                setError(null);
                loadCalendarStatus();
              }}
            >
              Retry
            </Button>
          </Alert>
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
              <CalendarCheckIcon className="h-5 w-5 text-green-600" />
              Calendar Connected
            </>
          ) : (
            <>
              <CalendarXIcon className="h-5 w-5 text-muted-foreground" />
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
                        <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">{cal.summary}</p>
                          {cal.description && (
                            <p className="text-xs text-muted-foreground">
                              {cal.description}
                            </p>
                          )}
                          {cal.primary && (
                            <Badge variant="secondary" className="text-xs mt-1">
                              Primary
                            </Badge>
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
