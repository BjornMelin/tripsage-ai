/**
 * @fileoverview Connection status monitor component for real-time connections.
 */

"use client";

import {
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  RefreshCwIcon,
  WifiIcon,
  WifiOffIcon,
  XCircleIcon,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useShallow } from "zustand/react/shallow";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import { useRealtimeConnectionStore } from "@/features/realtime/store/realtime-connection-store";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";
import type { ToneVariant } from "@/lib/variants/status";
import { statusVariants } from "@/lib/variants/status";

interface ConnectionStatus {
  isConnected: boolean;
  lastError: Error | null;
  connectedCount: number;
  totalCount: number;
  lastErrorAt: Date | null;
  reconnectAttempts: number;
  lastReconnectAt: Date | null;
}

interface RealtimeConnection {
  id: string;
  table: string;
  status: "connected" | "disconnected" | "error" | "reconnecting" | "connecting";
  error?: Error;
  lastActivity: Date | null;
}

function NormalizeTopic(topic: string): string {
  return topic.replace(/^realtime:/i, "");
}

function StatusIcon({
  isConnected,
  hasError,
  size = "h-4 w-4",
}: {
  isConnected: boolean;
  hasError: boolean;
  size?: string;
}) {
  if (hasError)
    return <AlertTriangleIcon aria-hidden="true" className={`${size} text-warning`} />;
  if (isConnected)
    return (
      <WifiIcon aria-hidden="true" className={`${size} text-success animate-pulse`} />
    );
  return <WifiOffIcon aria-hidden="true" className={`${size} text-destructive`} />;
}

/**
 * Component for monitoring real-time connection status
 * Shows overall connectivity, individual subscriptions, and provides reconnection controls
 */
export function ConnectionStatusMonitor() {
  const { toast } = useToast();
  const {
    connections: connectionsById,
    isReconnecting,
    reconnectAll,
    summary,
  } = useRealtimeConnectionStore(
    useShallow((state) => ({
      connections: state.connections,
      isReconnecting: state.isReconnecting,
      reconnectAll: state.reconnectAll,
      summary: state.summary,
    }))
  );
  const connections = useMemo(
    () =>
      Object.values(connectionsById).map((conn) => ({
        error: conn.lastError ?? undefined,
        id: conn.id,
        lastActivity: conn.lastActivity,
        status: conn.status,
        table: NormalizeTopic(conn.id),
      })),
    [connectionsById]
  );
  const connectionStatus: ConnectionStatus = useMemo(() => summary(), [summary]);
  const [showDetails, setShowDetails] = useState(false);

  const handleReconnectAll = async () => {
    if (isReconnecting) {
      return;
    }
    try {
      await reconnectAll();

      toast({
        description: "All real-time connections have been restored.",
        title: "Reconnected",
      });
    } catch (_error) {
      const error = _error as Error;
      recordClientErrorOnActiveSpan(error);
      toast({
        description: "Failed to restore some connections. Please try again.",
        title: "Reconnection Failed",
        variant: "destructive",
      });
    }
  };

  const getStatusBadge = (status: RealtimeConnection["status"]) => {
    // Disconnected uses "unknown" (neutral slate) to distinguish from actual errors.
    const statusMap: Record<
      RealtimeConnection["status"],
      { label: string; tone: ToneVariant }
    > = {
      connected: { label: "Connected", tone: "active" },
      connecting: { label: "Connecting…", tone: "pending" },
      disconnected: { label: "Disconnected", tone: "unknown" },
      error: { label: "Error", tone: "error" },
      reconnecting: { label: "Reconnecting…", tone: "pending" },
    };

    const config = statusMap[status];
    if (!config) return null;

    return (
      <Badge className={cn(statusVariants({ excludeRing: true, tone: config.tone }))}>
        {config.label}
      </Badge>
    );
  };

  const connectionHealthPercentage =
    connections.length > 0
      ? (connections.filter((c) => c.status === "connected").length /
          connections.length) *
        100
      : 0;

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <StatusIcon
              isConnected={connectionStatus.isConnected}
              hasError={!!connectionStatus.lastError}
            />
            <CardTitle className="text-sm">Real-time Status</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
          >
            <ActivityIcon aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>

        <CardDescription className="text-xs">
          {connectionStatus.connectedCount} of {connectionStatus.totalCount} connections
          active
        </CardDescription>

        <div className="space-y-2">
          <Progress value={connectionHealthPercentage} className="h-2" />
          <div className="text-xs text-muted-foreground">
            Connection Health: {Math.round(connectionHealthPercentage)}%
          </div>
        </div>
      </CardHeader>

      {showDetails && (
        <CardContent className="pt-0">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Connections</span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReconnectAll}
                disabled={isReconnecting}
              >
                {isReconnecting ? (
                  <RefreshCwIcon aria-hidden="true" className="h-3 w-3 animate-spin" />
                ) : (
                  <RefreshCwIcon aria-hidden="true" className="h-3 w-3" />
                )}
                {isReconnecting ? "Reconnecting…" : "Reconnect All"}
              </Button>
            </div>

            <div className="space-y-2">
              {connections.map((connection) => (
                <div
                  key={connection.id}
                  className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                >
                  <div className="flex items-center space-x-2">
                    {connection.status === "connected" ? (
                      <CheckCircleIcon
                        aria-hidden="true"
                        className="h-3 w-3 text-success"
                      />
                    ) : (
                      <XCircleIcon
                        aria-hidden="true"
                        className="h-3 w-3 text-destructive"
                      />
                    )}
                    <span className="text-xs font-medium">{connection.table}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    {getStatusBadge(connection.status)}
                    <span className="text-[10px] text-muted-foreground">
                      {connection.lastActivity
                        ? `Last activity ${connection.lastActivity.toLocaleTimeString()}`
                        : "Awaiting activity"}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {connectionStatus.lastError && (
              <>
                <Separator />
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <AlertTriangleIcon
                      aria-hidden="true"
                      className="h-4 w-4 text-warning"
                    />
                    <span className="text-sm font-medium">Last Error</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {connectionStatus.lastError.message}
                  </p>
                </div>
              </>
            )}

            <Separator />

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <div className="font-medium">Reconnect Attempts</div>
                <div className="text-muted-foreground">
                  {connectionStatus.reconnectAttempts}
                </div>
              </div>
              <div>
                <div className="font-medium">Last Reconnect</div>
                <div className="text-muted-foreground">
                  {connectionStatus.lastReconnectAt
                    ? connectionStatus.lastReconnectAt.toLocaleTimeString()
                    : "Never"}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

/**
 * Compact connection status indicator for navigation/header
 */
export function ConnectionStatusIndicator() {
  const { isConnected, lastError } = useRealtimeConnectionStore(
    useShallow((state) => {
      const summary = state.summary();
      return { isConnected: summary.isConnected, lastError: summary.lastError };
    })
  );
  const hasError = Boolean(lastError);

  return (
    <div className="flex items-center space-x-2">
      <StatusIcon isConnected={isConnected} hasError={hasError} size="h-3 w-3" />
      <span className="text-xs text-muted-foreground">
        {isConnected ? "Live" : "Offline"}
      </span>
    </div>
  );
}
