"use client";

import React, { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import {
  Wifi,
  WifiOff,
  Loader2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ConnectionStatus } from "@/lib/websocket/websocket-client";

interface ConnectionStatusProps {
  status: ConnectionStatus;
  onReconnect?: () => void;
  className?: string;
  compact?: boolean;
}

export default function ConnectionStatus({
  status,
  onReconnect,
  className,
  compact = false,
}: ConnectionStatusProps) {
  const [showStatus, setShowStatus] = useState(false);
  const [lastConnectedTime, setLastConnectedTime] = useState<Date | null>(null);

  // Show status indicator when not connected or when explicitly shown
  useEffect(() => {
    if (status === "connected") {
      setLastConnectedTime(new Date());
      // Hide status after 2 seconds when connected
      const timer = setTimeout(() => setShowStatus(false), 2000);
      return () => clearTimeout(timer);
    } else {
      setShowStatus(true);
    }
  }, [status]);

  // Auto-hide connected status after a delay
  useEffect(() => {
    if (status === "connected" && showStatus) {
      const timer = setTimeout(() => setShowStatus(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [status, showStatus]);

  const getStatusConfig = () => {
    switch (status) {
      case "connected":
        return {
          icon: <CheckCircle2 className="h-4 w-4" />,
          label: "Connected",
          description: "Real-time messaging active",
          color: "text-green-500",
          bgColor: "bg-green-500/10",
          borderColor: "border-green-500/20",
          variant: "default" as const,
        };
      case "connecting":
        return {
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          label: "Connecting",
          description: "Establishing real-time connection...",
          color: "text-blue-500",
          bgColor: "bg-blue-500/10",
          borderColor: "border-blue-500/20",
          variant: "secondary" as const,
        };
      case "disconnected":
        return {
          icon: <WifiOff className="h-4 w-4" />,
          label: "Disconnected",
          description: "Using standard messaging mode",
          color: "text-orange-500",
          bgColor: "bg-orange-500/10",
          borderColor: "border-orange-500/20",
          variant: "outline" as const,
        };
      case "error":
        return {
          icon: <AlertTriangle className="h-4 w-4" />,
          label: "Connection Error",
          description: "Failed to establish real-time connection",
          color: "text-red-500",
          bgColor: "bg-red-500/10",
          borderColor: "border-red-500/20",
          variant: "destructive" as const,
        };
      default:
        return {
          icon: <Wifi className="h-4 w-4" />,
          label: "Unknown",
          description: "Connection status unknown",
          color: "text-gray-500",
          bgColor: "bg-gray-500/10",
          borderColor: "border-gray-500/20",
          variant: "outline" as const,
        };
    }
  };

  const config = getStatusConfig();

  // Don't show when connected and compact mode (unless forcing show)
  if (status === "connected" && compact && !showStatus) {
    return null;
  }

  // Compact mode - just the badge
  if (compact) {
    return (
      <Badge
        variant={config.variant}
        className={cn(
          "flex items-center gap-1 text-xs",
          config.color,
          className
        )}
        onClick={() => status === "error" && onReconnect?.()}
      >
        {config.icon}
        {config.label}
      </Badge>
    );
  }

  // Don't show full status for connected state unless forcing show
  if (status === "connected" && !showStatus) {
    return null;
  }

  return (
    <div
      className={cn(
        "flex items-center justify-between p-3 rounded-lg border transition-all duration-200",
        config.bgColor,
        config.borderColor,
        className
      )}
    >
      <div className="flex items-center gap-3">
        <div className={cn("flex-shrink-0", config.color)}>{config.icon}</div>

        <div className="flex-1 min-w-0">
          <div className={cn("font-medium text-sm", config.color)}>
            {config.label}
          </div>
          <div className="text-xs text-muted-foreground">
            {config.description}
          </div>
          {lastConnectedTime && status !== "connected" && (
            <div className="text-xs text-muted-foreground mt-1">
              Last connected: {lastConnectedTime.toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {/* Reconnect button for error states */}
      {status === "error" && onReconnect && (
        <Button
          variant="outline"
          size="sm"
          onClick={onReconnect}
          className="ml-2"
        >
          Retry
        </Button>
      )}

      {/* Close button for connected state */}
      {status === "connected" && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowStatus(false)}
          className="ml-2 h-6 w-6 p-0"
        >
          ×
        </Button>
      )}
    </div>
  );
}
