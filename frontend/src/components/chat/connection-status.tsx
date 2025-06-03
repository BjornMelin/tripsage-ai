"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  AlertCircle,
  CheckCircle,
  Loader2,
  RefreshCw,
  Wifi,
  WifiOff,
} from "lucide-react";
import { memo } from "react";

export interface ConnectionStatusProps {
  status: "connecting" | "connected" | "disconnected" | "error";
  onReconnect?: () => void;
  className?: string;
}

export const ConnectionStatus = memo(function ConnectionStatus({
  status,
  onReconnect,
  className,
}: ConnectionStatusProps) {
  const getStatusConfig = () => {
    switch (status) {
      case "connecting":
        return {
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          text: "Connecting...",
          variant: "default" as const,
          showReconnect: false,
        };
      case "connected":
        return {
          icon: <CheckCircle className="h-4 w-4 text-green-500" />,
          text: "Connected",
          variant: "default" as const,
          showReconnect: false,
        };
      case "disconnected":
        return {
          icon: <WifiOff className="h-4 w-4 text-orange-500" />,
          text: "Disconnected - Messages will be sent when reconnected",
          variant: "default" as const,
          showReconnect: true,
        };
      case "error":
        return {
          icon: <AlertCircle className="h-4 w-4 text-red-500" />,
          text: "Connection failed - Check your internet connection",
          variant: "destructive" as const,
          showReconnect: true,
        };
    }
  };

  // Don't show anything when connected
  if (status === "connected") {
    return null;
  }

  const config = getStatusConfig();

  return (
    <Alert variant={config.variant} className={cn("mx-4 mb-2", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {config.icon}
          <AlertDescription className="font-medium">{config.text}</AlertDescription>
        </div>

        {config.showReconnect && onReconnect && (
          <Button variant="outline" size="sm" onClick={onReconnect} className="ml-4">
            <RefreshCw className="h-3 w-3 mr-1" />
            Reconnect
          </Button>
        )}
      </div>
    </Alert>
  );
});

// Compact version for header/status bar
export const CompactConnectionStatus = memo(function CompactConnectionStatus({
  status,
  onReconnect,
  className,
}: ConnectionStatusProps) {
  const getStatusConfig = () => {
    switch (status) {
      case "connecting":
        return {
          icon: <Loader2 className="h-3 w-3 animate-spin text-blue-500" />,
          text: "Connecting",
          color: "text-blue-500",
        };
      case "connected":
        return {
          icon: <Wifi className="h-3 w-3 text-green-500" />,
          text: "Online",
          color: "text-green-500",
        };
      case "disconnected":
        return {
          icon: <WifiOff className="h-3 w-3 text-orange-500" />,
          text: "Offline",
          color: "text-orange-500",
        };
      case "error":
        return {
          icon: <AlertCircle className="h-3 w-3 text-red-500" />,
          text: "Error",
          color: "text-red-500",
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {config.icon}
      <span className={cn("text-xs font-medium", config.color)}>{config.text}</span>

      {(status === "disconnected" || status === "error") && onReconnect && (
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 ml-1"
          onClick={onReconnect}
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
});
