"use client";

import type React from "react";
import { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import {
  Wifi,
  WifiOff,
  Signal,
  SignalHigh,
  SignalLow,
  SignalMedium,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Zap,
  Router,
  Monitor,
  RefreshCw,
  Info,
} from "lucide-react";

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

export interface NetworkMetrics {
  latency: number;
  bandwidth: number;
  packetLoss: number;
  jitter: number;
  quality: "excellent" | "good" | "fair" | "poor";
  signalStrength: number; // 0-100
}

export interface ConnectionAnalytics {
  connectionTime: number;
  reconnectCount: number;
  totalMessages: number;
  failedMessages: number;
  avgResponseTime: number;
  lastDisconnection?: Date;
  uptime: number; // in seconds
}

interface EnhancedConnectionStatusProps {
  status: ConnectionStatus;
  metrics?: NetworkMetrics;
  analytics?: ConnectionAnalytics;
  onReconnect?: () => void;
  onOptimize?: () => void;
  className?: string;
  compact?: boolean;
  showMetrics?: boolean;
  showOptimizations?: boolean;
}

const defaultMetrics: NetworkMetrics = {
  latency: 0,
  bandwidth: 0,
  packetLoss: 0,
  jitter: 0,
  quality: "poor",
  signalStrength: 0,
};

const defaultAnalytics: ConnectionAnalytics = {
  connectionTime: 0,
  reconnectCount: 0,
  totalMessages: 0,
  failedMessages: 0,
  avgResponseTime: 0,
  uptime: 0,
};

const getQualityColor = (quality: NetworkMetrics["quality"]) => {
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

const getSignalIcon = (strength: number) => {
  if (strength >= 80) return <SignalHigh className="h-4 w-4" />;
  if (strength >= 60) return <SignalMedium className="h-4 w-4" />;
  if (strength >= 40) return <SignalLow className="h-4 w-4" />;
  return <Signal className="h-4 w-4" />;
};

const formatLatency = (ms: number) => {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

const formatBandwidth = (bps: number) => {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${(bps / (1024 * 1024)).toFixed(1)} MB/s`;
};

const formatUptime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
};

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
        {Array.from({ length: 4 }, (_, i) => (
          <motion.div
            key={i}
            className={cn(
              "w-1 rounded-full",
              qualityScore > (i + 1) * 25 ? "bg-green-500" : "bg-gray-300"
            )}
            style={{ height: `${8 + i * 2}px` }}
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            transition={{ delay: i * 0.1 }}
          />
        ))}
      </div>
      <span className={cn("text-sm font-medium", getQualityColor(metrics.quality))}>
        {metrics.quality}
      </span>
    </div>
  );
};

const NetworkOptimizationSuggestions: React.FC<{
  metrics: NetworkMetrics;
  onOptimize?: () => void;
}> = ({ metrics, onOptimize }) => {
  const suggestions = useMemo(() => {
    const items = [];

    if (metrics.latency > 200) {
      items.push({
        icon: <TrendingDown className="h-4 w-4 text-red-500" />,
        title: "High Latency Detected",
        description: "Consider switching to a closer server location",
        action: "Optimize Route",
      });
    }

    if (metrics.packetLoss > 2) {
      items.push({
        icon: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
        title: "Packet Loss Detected",
        description: "Network connection may be unstable",
        action: "Check Network",
      });
    }

    if (metrics.bandwidth < 1000000) {
      items.push({
        icon: <TrendingUp className="h-4 w-4 text-blue-500" />,
        title: "Low Bandwidth",
        description: "Consider reducing data frequency",
        action: "Optimize Data",
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
          {suggestions.map((suggestion, index) => (
            <div key={index} className="flex items-center justify-between">
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

export const EnhancedConnectionStatus: React.FC<EnhancedConnectionStatusProps> = ({
  status,
  metrics = defaultMetrics,
  analytics = defaultAnalytics,
  onReconnect,
  onOptimize,
  className,
  compact = false,
  showMetrics = true,
  showOptimizations = true,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (status === "connecting" || status === "reconnecting") {
      setIsAnimating(true);
    } else {
      setIsAnimating(false);
    }
  }, [status]);

  const getStatusConfig = () => {
    switch (status) {
      case "connected":
        return {
          icon: <CheckCircle2 className="h-4 w-4" />,
          label: "Connected",
          description: "Real-time connection active",
          color: "text-green-500",
          bgColor: "bg-green-500/10",
          borderColor: "border-green-500/20",
          variant: "default" as const,
        };
      case "connecting":
        return {
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          label: "Connecting",
          description: "Establishing connection...",
          color: "text-blue-500",
          bgColor: "bg-blue-500/10",
          borderColor: "border-blue-500/20",
          variant: "secondary" as const,
        };
      case "reconnecting":
        return {
          icon: <RefreshCw className="h-4 w-4 animate-spin" />,
          label: "Reconnecting",
          description: `Attempt ${analytics.reconnectCount + 1}`,
          color: "text-orange-500",
          bgColor: "bg-orange-500/10",
          borderColor: "border-orange-500/20",
          variant: "secondary" as const,
        };
      case "disconnected":
        return {
          icon: <WifiOff className="h-4 w-4" />,
          label: "Disconnected",
          description: "No real-time connection",
          color: "text-gray-500",
          bgColor: "bg-gray-500/10",
          borderColor: "border-gray-500/20",
          variant: "outline" as const,
        };
      case "error":
        return {
          icon: <AlertTriangle className="h-4 w-4" />,
          label: "Connection Error",
          description: "Failed to establish connection",
          color: "text-red-500",
          bgColor: "bg-red-500/10",
          borderColor: "border-red-500/20",
          variant: "destructive" as const,
        };
      default:
        return {
          icon: <Wifi className="h-4 w-4" />,
          label: "Unknown",
          description: "Status unknown",
          color: "text-gray-500",
          bgColor: "bg-gray-500/10",
          borderColor: "border-gray-500/20",
          variant: "outline" as const,
        };
    }
  };

  const config = getStatusConfig();

  if (compact) {
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
                  {getSignalIcon(metrics.signalStrength)}
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
                  <div>Latency: {formatLatency(metrics.latency)}</div>
                  <div>Quality: {metrics.quality}</div>
                  <div>Uptime: {formatUptime(analytics.uptime)}</div>
                </div>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <Card className={cn("transition-all duration-300", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              className={cn("flex-shrink-0", config.color)}
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
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
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
                          {formatLatency(metrics.latency)}
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
                          {formatBandwidth(metrics.bandwidth)}
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
                          {formatUptime(analytics.uptime)}
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
                    {formatLatency(analytics.avgResponseTime)}
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

export default EnhancedConnectionStatus;
