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
import { useEffect, useState } from "react";
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
  lastActivity?: Date;
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

  // Mock data for demonstration - in real implementation, this would come from a global store
  useEffect(() => {
    const mockConnections: RealtimeConnection[] = [
      {
        id: "trips-realtime",
        lastActivity: new Date(),
        status: "connected",
        table: "trips",
      },
      {
        id: "chat-messages-realtime",
        lastActivity: new Date(Date.now() - 30000),
        status: "connected",
        table: "chat_messages",
      },
      {
        error: new Error("Connection timeout"),
        id: "trip-collaborators-realtime",
        status: "disconnected",
        table: "trip_collaborators",
      },
    ];

    setConnections(mockConnections);
    setConnectionStatus({
      connectionCount: mockConnections.filter((c) => c.status === "connected").length,
      isConnected: mockConnections.some((c) => c.status === "connected"),
      lastError: mockConnections.find((c) => c.error)?.error || null,
      lastReconnectAt: null,
      reconnectAttempts: 0,
    });
  }, []);

  const handleReconnectAll = async () => {
    setIsReconnecting(true);
    try {
      // Simulate reconnection delay
      await new Promise((resolve) => setTimeout(resolve, 2000));

      setConnections((prev) =>
        prev.map((conn) => ({
          ...conn,
          error: undefined,
          lastActivity: new Date(),
          status: "connected" as const,
        }))
      );

      setConnectionStatus((prev) => ({
        ...prev,
        connectionCount: connections.length,
        isConnected: true,
        lastError: null,
        lastReconnectAt: new Date(),
        reconnectAttempts: prev.reconnectAttempts + 1,
      }));

      toast({
        description: "All real-time connections have been restored.",
        title: "Reconnected",
      });
    } catch (_error) {
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
