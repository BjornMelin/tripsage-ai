/**
 * @fileoverview Client-side helpers for the security dashboard: local time rendering
 * and interactive session controls.
 */

"use client";

import type { ActiveSession, SecurityEvent, SecurityMetrics } from "@schemas/security";
import { AlertTriangle, CheckCircle2, Monitor, Shield, Smartphone } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";

/** Local time props. */
type LocalTimeProps = {
  isoString: string;
  className?: string;
};

/**
 * Render an ISO timestamp in the viewer's locale/timezone.
 *
 * @param isoString - The ISO timestamp to render.
 * @param className - The class name to apply to the rendered timestamp.
 * @returns The rendered timestamp.
 */
export function LocalTime({ isoString, className }: LocalTimeProps) {
  const [formatted, setFormatted] = useState<string>("—");

  useEffect(() => {
    try {
      const date = new Date(isoString);
      if (Number.isNaN(date.getTime())) {
        setFormatted("Invalid date");
        return;
      }
      const formatter = new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
      setFormatted(formatter.format(date));
    } catch {
      setFormatted("Invalid date");
    }
  }, [isoString]);

  return <span className={className}>{formatted}</span>;
}

/** Security events list props. */
type SecurityEventsListProps = {
  events: SecurityEvent[];
  riskColor: Record<SecurityEvent["riskLevel"], string>;
};

/**
 * Display recent security events with risk coloring and client-local timestamps.
 *
 * @param events - The security events to render.
 * @param riskColor - The risk color for each security event risk level.
 * @returns The rendered security events list.
 */
export function SecurityEventsList({ events, riskColor }: SecurityEventsListProps) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No recent events.</p>;
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.id} className="border rounded-md p-3 space-y-1">
          <div className="flex items-center justify-between text-sm font-semibold">
            <span>{event.description}</span>
            <span className={riskColor[event.riskLevel]}>{event.riskLevel}</span>
          </div>
          <div className="text-xs text-muted-foreground flex gap-3">
            <LocalTime isoString={event.timestamp} />
            <span>{event.ipAddress}</span>
            {event.device ? <span>{event.device}</span> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Active sessions list props. */
type ActiveSessionsListProps = {
  sessions: ActiveSession[];
};

/**
 * Interactive list of active sessions with terminate controls for non-current entries.
 *
 * @param sessions - The active sessions to render.
 * @returns The rendered active sessions list.
 */
export function ActiveSessionsList({ sessions }: ActiveSessionsListProps) {
  const [currentSessions, setCurrentSessions] = useState<ActiveSession[]>(sessions);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const { toast } = useToast();

  const sortedSessions = useMemo(
    () =>
      [...currentSessions].sort((a, b) => {
        if (a.isCurrent === b.isCurrent) {
          return (
            new Date(b.lastActivity).getTime() - new Date(a.lastActivity).getTime()
          );
        }
        return a.isCurrent ? -1 : 1;
      }),
    [currentSessions]
  );

  /**
   * Handle the termination of a session.
   *
   * @param sessionId - The ID of the session to terminate.
   */
  const handleTerminate = async (sessionId: string) => {
    try {
      setPendingId(sessionId);
      const response = await fetch(`/api/security/sessions/${sessionId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(`Failed to terminate session (${response.status})`);
      }
      setCurrentSessions((prev) => prev.filter((session) => session.id !== sessionId));
      toast({
        description: "The selected session has been revoked.",
        title: "Session terminated",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast({
        description: message,
        title: "Unable to terminate session",
        variant: "destructive",
      });
    } finally {
      setPendingId(null);
    }
  };

  if (sortedSessions.length === 0) {
    return <p className="text-sm text-muted-foreground">No active sessions.</p>;
  }

  return (
    <div className="space-y-3">
      {sortedSessions.map((session) => (
        <div key={session.id} className="border rounded-md p-3 space-y-1">
          <div className="flex items-center justify-between text-sm font-semibold">
            <span className="flex items-center gap-2">
              <Smartphone className="h-4 w-4" />
              {session.device}
            </span>
            {session.isCurrent ? (
              <span className="text-green-600 text-xs flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Current session
              </span>
            ) : (
              <Button
                variant="destructive"
                size="sm"
                className="h-7 px-3 text-xs"
                disabled={pendingId === session.id}
                onClick={() => handleTerminate(session.id)}
              >
                {pendingId === session.id ? "Terminating..." : "Terminate"}
              </Button>
            )}
          </div>
          <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-3">
            <span>{session.browser}</span>
            <span>{session.ipAddress}</span>
            <LocalTime isoString={session.lastActivity} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Connections summary props. */
type ConnectionsSummaryProps = {
  metrics: SecurityMetrics;
};

/**
 * Present connection metadata with client-local timestamp formatting.
 *
 * @param metrics - The security metrics to render.
 * @returns The rendered connections summary.
 */
export function ConnectionsSummary({ metrics }: ConnectionsSummaryProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm">
        <Shield className="h-4 w-4" />
        Last login: <LocalTime isoString={metrics.lastLogin} className="font-medium" />
      </div>
      <div className="flex items-center gap-2 text-sm">
        <Monitor className="h-4 w-4" />
        OAuth: {metrics.oauthConnections.join(", ") || "None"}
      </div>
      <div className="flex items-center gap-2 text-sm">
        <AlertTriangle className="h-4 w-4 text-red-600" />
        Trusted devices: {metrics.trustedDevices}
      </div>
    </div>
  );
}
