/**
 * @fileoverview Connection status component with real-time network metrics and analytics.
 */

"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  Monitor,
  RefreshCw,
  Router,
  Signal,
  SignalHigh,
  SignalLow,
  SignalMedium,
  TrendingDown,
  TrendingUp,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// Type for the connection status
export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

// Type for the network metrics interface
export interface NetworkMetrics {
  latency: number;
  bandwidth: number;
  packetLoss: number;
  jitter: number;
  quality: "excellent" | "good" | "fair" | "poor";
  signalStrength: number; // 0-100
}

// Type for the connection analytics interface
export interface ConnectionAnalytics {
  connectionTime: number;
  reconnectCount: number;
  totalMessages: number;
  failedMessages: number;
  avgResponseTime: number;
  lastDisconnection?: Date;
  uptime: number; // in seconds
}

// Type for the connection status props
interface ConnectionStatusProps {
  status: ConnectionStatus;
  metrics?: NetworkMetrics;
  analytics?: ConnectionAnalytics;
  onReconnect?: () => void;
  onOptimize?: () => void;
  className?: string;
  variant?: "default" | "compact" | "minimal" | "detailed";
  showMetrics?: boolean;
  showOptimizations?: boolean;
}

// Default metrics for the connection status
const DefaultMetrics: NetworkMetrics = {
  bandwidth: 0,
  jitter: 0,
  latency: 0,
  packetLoss: 0,
  quality: "poor",
  signalStrength: 0,
};

// Default analytics for the connection status
const DefaultAnalytics: ConnectionAnalytics = {
  avgResponseTime: 0,
  connectionTime: 0,
  failedMessages: 0,
  reconnectCount: 0,
  totalMessages: 0,
  uptime: 0,
};

/**
 * Get the quality color for the connection status
 *
 * @param quality - The quality of the connection
 * @returns The quality color
 */
const GetQualityColor = (quality: NetworkMetrics["quality"]) => {
  switch (quality) {
    case "excellent":
      return "text-green-500";
    case "good":
      return "text-blue-500";
    case "fair":
      return "text-yellow-500";
    case "poor":
      return "text-red-500";
    default:
      return "text-gray-500";
  }
};
/**
 * Get the signal icon for the connection status
 *
 * @param strength - The signal strength
 * @returns The signal icon
 */
const GetSignalIcon = (strength: number) => {
  if (strength >= 80) return <SignalHigh className="h-4 w-4" />;
  if (strength >= 60) return <SignalMedium className="h-4 w-4" />;
  if (strength >= 40) return <SignalLow className="h-4 w-4" />;
  return <Signal className="h-4 w-4" />;
};

/**
 * Format the latency for the connection status
 *
 * @param ms - The latency in milliseconds
 * @returns The formatted latency
 */
const FormatLatency = (ms: number) => {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

/**
 * Format the bandwidth for the connection status
 *
 * @param bps - The bandwidth in bits per second
 * @returns The formatted bandwidth
 */
const FormatBandwidth = (bps: number) => {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${(bps / (1024 * 1024)).toFixed(1)} MB/s`;
};

/**
 * Format the uptime for the connection status
 *
 * @param seconds - The uptime in seconds
 * @returns The formatted uptime
 */
const FormatUptime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
};

/**
 * Connection quality indicator component
 *
 * @param metrics - The network metrics
 * @returns The connection quality indicator
 */
const ConnectionQualityIndicator: React.FC<{ metrics: NetworkMetrics }> = ({
  metrics,
}) => {
  const qualityScore = useMemo(() => {
    // Calculate quality score based on multiple factors
    const latencyScore = Math.max(0, 100 - metrics.latency / 10); // Good latency < 100ms
    const bandwidthScore = Math.min(100, (metrics.bandwidth / 1000000) * 20); // Good bandwidth > 5MB/s
    const lossScore = Math.max(0, 100 - metrics.packetLoss * 20); // Good loss < 5%
    const jitterScore = Math.max(0, 100 - metrics.jitter / 2); // Good jitter < 10ms

    return (latencyScore + bandwidthScore + lossScore + jitterScore) / 4;
  }, [metrics]);

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1">
        {[
          { height: 8, key: "bar-0", threshold: 0 },
          { height: 10, key: "bar-1", threshold: 25 },
          { height: 12, key: "bar-2", threshold: 50 },
          { height: 14, key: "bar-3", threshold: 75 },
        ].map(({ key, height, threshold }) => (
          <motion.div
            key={key}
            className={cn(
              "w-1 rounded-full",
              qualityScore >= threshold ? "bg-green-500" : "bg-gray-300"
            )}
            style={{ height: `${height}px` }}
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            transition={{ delay: parseInt(key.split("-")[1], 10) * 0.1 }}
          />
        ))}
      </div>
      <span className={cn("text-sm font-medium", GetQualityColor(metrics.quality))}>
        {metrics.quality}
      </span>
    </div>
  );
};

/**
 * Network optimization suggestions component
 *
 * @param metrics - The network metrics
 * @param onOptimize - The function to optimize the network
 * @returns The network optimization suggestions
 */
const NetworkOptimizationSuggestions: React.FC<{
  metrics: NetworkMetrics;
  onOptimize?: () => void;
}> = ({ metrics, onOptimize }) => {
  const suggestions = useMemo(() => {
    const items = [];

    if (metrics.latency > 200) {
      items.push({
        action: "Optimize Route",
        description: "Consider switching to a closer server location",
        icon: <TrendingDown className="h-4 w-4 text-red-500" />,
        title: "High Latency Detected",
      });
    }

    if (metrics.packetLoss > 2) {
      items.push({
        action: "Check Network",
        description: "Network connection may be unstable",
        icon: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
        title: "Packet Loss Detected",
      });
    }

    if (metrics.bandwidth < 1000000) {
      items.push({
        action: "Optimize Data",
        description: "Consider reducing data frequency",
        icon: <TrendingUp className="h-4 w-4 text-blue-500" />,
        title: "Low Bandwidth",
      });
    }

    return items;
  }, [metrics]);

  if (suggestions.length === 0) return null;

  return (
    <Alert className="mt-3">
      <Info className="h-4 w-4" />
      <AlertDescription>
        <div className="space-y-2">
          {suggestions.map((suggestion) => (
            <div key={suggestion.title} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {suggestion.icon}
                <div>
                  <div className="text-sm font-medium">{suggestion.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {suggestion.description}
                  </div>
                </div>
              </div>
              {onOptimize && (
                <Button variant="outline" size="sm" onClick={onOptimize}>
                  {suggestion.action}
                </Button>
              )}
            </div>
          ))}
        </div>
      </AlertDescription>
    </Alert>
  );
};

/**
 * Connection status component
 *
 * @param props - The connection status props
 * @returns The connection status component
 */
export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  status,
  metrics = DefaultMetrics,
  analytics = DefaultAnalytics,
  onReconnect,
  onOptimize,
  className,
  variant = "default",
  showMetrics = true,
  showOptimizations = true,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [lastConnectedTime, setLastConnectedTime] = useState<Date | null>(null);

  useEffect(() => {
    if (status === "connecting" || status === "reconnecting") {
      setIsAnimating(true);
    } else {
      setIsAnimating(false);
    }

    if (status === "connected") {
      setLastConnectedTime(new Date());
    }
  }, [status]);

  const getStatusConfig = () => {
    switch (status) {
      case "connected":
        return {
          bgColor: "bg-green-500/10",
          borderColor: "border-green-500/20",
          color: "text-green-500",
          description: "Real-time connection active",
          icon: <CheckCircle2 className="h-4 w-4" />,
          label: "Connected",
          variant: "default" as const,
        };
      case "connecting":
        return {
          bgColor: "bg-blue-500/10",
          borderColor: "border-blue-500/20",
          color: "text-blue-500",
          description: "Establishing connection...",
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          label: "Connecting",
          variant: "default" as const,
        };
      case "reconnecting":
        return {
          bgColor: "bg-orange-500/10",
          borderColor: "border-orange-500/20",
          color: "text-orange-500",
          description: `Attempt ${analytics.reconnectCount + 1}`,
          icon: <RefreshCw className="h-4 w-4 animate-spin" />,
          label: "Reconnecting",
          variant: "default" as const,
        };
      case "disconnected":
        return {
          bgColor: "bg-gray-500/10",
          borderColor: "border-gray-500/20",
          color: "text-gray-500",
          description: "No real-time connection",
          icon: <WifiOff className="h-4 w-4" />,
          label: "Disconnected",
          variant: "default" as const,
        };
      case "error":
        return {
          bgColor: "bg-red-500/10",
          borderColor: "border-red-500/20",
          color: "text-red-500",
          description: "Failed to establish connection",
          icon: <AlertTriangle className="h-4 w-4" />,
          label: "Connection Error",
          variant: "destructive" as const,
        };
      default:
        return {
          bgColor: "bg-gray-500/10",
          borderColor: "border-gray-500/20",
          color: "text-gray-500",
          description: "Status unknown",
          icon: <Wifi className="h-4 w-4" />,
          label: "Unknown",
          variant: "default" as const,
        };
    }
  };

  const config = getStatusConfig();

  // Minimal variant - just icon and status for status bars
  if (variant === "minimal") {
    return (
      <div className={cn("flex items-center gap-1.5", className)}>
        <div className={cn("shrink-0", config.color)}>{config.icon}</div>
        <span className={cn("text-xs font-medium", config.color)}>
          {status === "connected" ? "Online" : config.label}
        </span>
      </div>
    );
  }

  // Compact variant - badge format
  if (variant === "compact") {
    // Don't show when connected unless there's an issue
    if (status === "connected" && !showDetails) {
      return null;
    }

    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge
              variant={config.variant}
              className={cn(
                "flex items-center gap-2 cursor-pointer transition-all duration-200",
                config.color,
                className
              )}
              onClick={() => setShowDetails(!showDetails)}
            >
              <motion.div
                animate={isAnimating ? { rotate: 360 } : {}}
                transition={{
                  duration: 1,
                  repeat: isAnimating ? Number.POSITIVE_INFINITY : 0,
                }}
              >
                {config.icon}
              </motion.div>
              {config.label}
              {status === "connected" && (
                <div className="flex items-center gap-1">
                  {GetSignalIcon(metrics.signalStrength)}
                  <span className="text-xs">{metrics.signalStrength}%</span>
                </div>
              )}
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              <div>{config.description}</div>
              {status === "connected" && showMetrics && (
                <div className="text-xs space-y-1">
                  <div>Latency: {FormatLatency(metrics.latency)}</div>
                  <div>Quality: {metrics.quality}</div>
                  <div>Uptime: {FormatUptime(analytics.uptime)}</div>
                </div>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Default variant - alert format for chat/messaging
  if (variant === "default") {
    // Don't show when connected
    if (status === "connected") {
      return null;
    }

    return (
      <Alert variant={config.variant} className={cn("mx-4 mb-2", className)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {config.icon}
            <AlertDescription className="font-medium">
              {config.description}
            </AlertDescription>
          </div>

          {(status === "error" || status === "disconnected") && onReconnect && (
            <Button variant="outline" size="sm" onClick={onReconnect} className="ml-4">
              <RefreshCw className="h-3 w-3 mr-1" />
              Reconnect
            </Button>
          )}
        </div>
      </Alert>
    );
  }

  // Detailed variant - full card with metrics
  return (
    <Card className={cn("transition-all duration-300", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              className={cn("shrink-0", config.color)}
              animate={isAnimating ? { rotate: 360 } : {}}
              transition={{
                duration: 1,
                repeat: isAnimating ? Number.POSITIVE_INFINITY : 0,
              }}
            >
              {config.icon}
            </motion.div>
            <div>
              <div className={cn("font-medium", config.color)}>{config.label}</div>
              <div className="text-sm text-muted-foreground">{config.description}</div>
              {lastConnectedTime && status !== "connected" && (
                <div className="text-xs text-muted-foreground mt-1">
                  Last connected: {lastConnectedTime.toLocaleTimeString()}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {status === "connected" && <ConnectionQualityIndicator metrics={metrics} />}
            {(status === "error" || status === "disconnected") && onReconnect && (
              <Button variant="outline" size="sm" onClick={onReconnect}>
                <RefreshCw className="h-4 w-4 mr-1" />
                Reconnect
              </Button>
            )}
          </div>
        </CardTitle>
      </CardHeader>

      <AnimatePresence>
        {status === "connected" && showMetrics && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <CardContent className="pt-0">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="text-center p-2 rounded-lg bg-gray-50">
                        <Activity className="h-4 w-4 mx-auto mb-1 text-blue-500" />
                        <div className="text-sm font-medium">
                          {FormatLatency(metrics.latency)}
                        </div>
                        <div className="text-xs text-muted-foreground">Latency</div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Round-trip time for messages</TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="text-center p-2 rounded-lg bg-gray-50">
                        <Zap className="h-4 w-4 mx-auto mb-1 text-green-500" />
                        <div className="text-sm font-medium">
                          {FormatBandwidth(metrics.bandwidth)}
                        </div>
                        <div className="text-xs text-muted-foreground">Bandwidth</div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Data transfer rate</TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="text-center p-2 rounded-lg bg-gray-50">
                        <Router className="h-4 w-4 mx-auto mb-1 text-orange-500" />
                        <div className="text-sm font-medium">
                          {metrics.packetLoss.toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground">Packet Loss</div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Percentage of lost data packets</TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="text-center p-2 rounded-lg bg-gray-50">
                        <Monitor className="h-4 w-4 mx-auto mb-1 text-purple-500" />
                        <div className="text-sm font-medium">
                          {FormatUptime(analytics.uptime)}
                        </div>
                        <div className="text-xs text-muted-foreground">Uptime</div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Connection uptime</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>

              {/* Signal Strength Indicator */}
              <div className="flex items-center gap-3 mb-3">
                <span className="text-sm text-muted-foreground">Signal Strength:</span>
                <div className="flex-1">
                  <Progress value={metrics.signalStrength} className="h-2" />
                </div>
                <span className="text-sm font-medium">{metrics.signalStrength}%</span>
              </div>

              {/* Analytics */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Messages:</span>
                  <span className="ml-2 font-medium">
                    {analytics.totalMessages}
                    {analytics.failedMessages > 0 && (
                      <span className="text-red-500">
                        {" "}
                        ({analytics.failedMessages} failed)
                      </span>
                    )}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Avg Response:</span>
                  <span className="ml-2 font-medium">
                    {FormatLatency(analytics.avgResponseTime)}
                  </span>
                </div>
              </div>

              {/* Network Optimization Suggestions */}
              {showOptimizations && (
                <NetworkOptimizationSuggestions
                  metrics={metrics}
                  onOptimize={onOptimize}
                />
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
};

export default ConnectionStatus;

export const CompactConnectionStatus = (props: ConnectionStatusProps) => (
  <ConnectionStatus {...props} variant="compact" />
);
