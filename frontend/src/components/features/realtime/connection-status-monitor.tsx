/**
 * @fileoverview Connection status monitor component for real-time connections.
 */

"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Wifi,
  WifiOff,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
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
import { type BackoffConfig, computeBackoffDelay } from "@/lib/realtime/backoff";
import { getBrowserClient, type TypedSupabaseClient } from "@/lib/supabase";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

interface ConnectionStatus {
  isConnected: boolean;
  lastError: Error | null;
  connectionCount: number;
  reconnectAttempts: number;
  lastReconnectAt: Date | null;
}

interface RealtimeConnection {
  id: string;
  table: string;
  status: "connected" | "disconnected" | "error" | "reconnecting";
  error?: Error;
  lastActivity: Date | null;
}

const BACKOFF_CONFIG: BackoffConfig = {
  factor: 2,
  initialDelayMs: 500,
  maxDelayMs: 8000,
};

function MapChannelStatus(state: string | undefined): RealtimeConnection["status"] {
  switch (state) {
    case "joined":
      return "connected";
    case "joining":
      return "reconnecting";
    case "errored":
      return "error";
    case "leaving":
    case "closed":
      return "disconnected";
    default:
      return "reconnecting";
  }
}

function NormalizeTopic(topic: string): string {
  return topic.replace(/^realtime:/i, "");
}

/**
 * Component for monitoring real-time connection status
 * Shows overall connectivity, individual subscriptions, and provides reconnection controls
 */
export function ConnectionStatusMonitor() {
  const { toast } = useToast();
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connectionCount: 0,
    isConnected: false,
    lastError: null,
    lastReconnectAt: null,
    reconnectAttempts: 0,
  });

  const [connections, setConnections] = useState<RealtimeConnection[]>([]);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const reconnectAttemptsRef = useRef(0);
  const lastReconnectAtRef = useRef<Date | null>(null);
  const previousConnectionsRef = useRef<Record<string, RealtimeConnection>>({});

  const refreshConnections = useCallback((client: TypedSupabaseClient) => {
    const now = new Date();
    const channels = client.realtime.getChannels();

    const nextConnections = channels.map((channel) => {
      const status = MapChannelStatus((channel as { state?: string }).state);
      const id = channel.topic;
      const previous = previousConnectionsRef.current[id];
      const lastActivity =
        status === "connected"
          ? (previous?.lastActivity ?? now)
          : (previous?.lastActivity ?? null);

      const error =
        status === "error"
          ? (previous?.error ?? new Error(`Realtime channel ${id} errored`))
          : undefined;

      return {
        error,
        id,
        lastActivity,
        status,
        table: NormalizeTopic(channel.topic),
      };
    });

    previousConnectionsRef.current = Object.fromEntries(
      nextConnections.map((conn) => [conn.id, conn])
    );

    const lastError = nextConnections.find((conn) => conn.error)?.error ?? null;
    if (lastError) {
      recordClientErrorOnActiveSpan(lastError);
    }

    setConnections(nextConnections);
    setConnectionStatus({
      connectionCount: nextConnections.filter((c) => c.status === "connected").length,
      isConnected: client.realtime.isConnected(),
      lastError,
      lastReconnectAt: lastReconnectAtRef.current,
      reconnectAttempts: reconnectAttemptsRef.current,
    });
  }, []);

  useEffect(() => {
    const supabase = getBrowserClient();
    if (!supabase) return;

    refreshConnections(supabase);
    const intervalId = window.setInterval(() => refreshConnections(supabase), 1500);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [refreshConnections]);

  const handleReconnectAll = async () => {
    const supabase = getBrowserClient();
    if (!supabase) {
      toast({
        description: "Supabase client is unavailable in this environment.",
        title: "Reconnection Failed",
        variant: "destructive",
      });
      return;
    }

    setIsReconnecting(true);
    reconnectAttemptsRef.current += 1;
    const attempt = reconnectAttemptsRef.current;
    const delay = computeBackoffDelay(attempt, BACKOFF_CONFIG);

    try {
      if (delay > 0) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }

      const channels = supabase.realtime.getChannels();
      for (const channel of channels) {
        try {
          await channel.unsubscribe();
        } catch {
          // ignore unsubscribe failures
        }
        channel.subscribe();
      }

      supabase.realtime.connect();

      const now = new Date();
      lastReconnectAtRef.current = now;

      refreshConnections(supabase);
      setConnectionStatus((prev) => ({
        ...prev,
        lastError: null,
        lastReconnectAt: now,
        reconnectAttempts: attempt,
      }));

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
    } finally {
      setIsReconnecting(false);
    }
  };

  const getStatusIcon = (isConnected: boolean, hasError: boolean) => {
    if (hasError) return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    if (isConnected) return <Wifi className="h-4 w-4 text-green-500" />;
    return <WifiOff className="h-4 w-4 text-red-500" />;
  };

  const getStatusBadge = (status: RealtimeConnection["status"]) => {
    switch (status) {
      case "connected":
        return (
          <Badge variant="default" className="bg-green-500">
            Connected
          </Badge>
        );
      case "disconnected":
        return <Badge variant="destructive">Disconnected</Badge>;
      case "error":
        return <Badge variant="destructive">Error</Badge>;
      case "reconnecting":
        return <Badge variant="secondary">Reconnecting...</Badge>;
    }
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
            {getStatusIcon(connectionStatus.isConnected, !!connectionStatus.lastError)}
            <CardTitle className="text-sm">Real-time Status</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
          >
            <Activity className="h-4 w-4" />
          </Button>
        </div>

        <CardDescription className="text-xs">
          {connectionStatus.connectionCount} of {connections.length} connections active
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
                  <RefreshCw className="h-3 w-3 animate-spin" />
                ) : (
                  <RefreshCw className="h-3 w-3" />
                )}
                {isReconnecting ? "Reconnecting..." : "Reconnect All"}
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
                      <CheckCircle className="h-3 w-3 text-green-500" />
                    ) : (
                      <XCircle className="h-3 w-3 text-red-500" />
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
                    <AlertTriangle className="h-4 w-4 text-yellow-500" />
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
  const [isConnected, _setIsConnected] = useState(true);
  const [hasError, _setHasError] = useState(false);

  return (
    <div className="flex items-center space-x-2">
      {GetStatusIcon(isConnected, hasError)}
      <span className="text-xs text-muted-foreground">
        {isConnected ? "Live" : "Offline"}
      </span>
    </div>
  );
}

function GetStatusIcon(isConnected: boolean, hasError: boolean) {
  if (hasError) return <AlertTriangle className="h-3 w-3 text-yellow-500" />;
  if (isConnected) return <Activity className="h-3 w-3 text-green-500 animate-pulse" />;
  return <WifiOff className="h-3 w-3 text-red-500" />;
}
