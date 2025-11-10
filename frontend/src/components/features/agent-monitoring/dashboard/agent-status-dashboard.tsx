/**
 * @fileoverview Agent status dashboard component for monitoring agent performance and status.
 */

"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle,
  Clock,
  Cpu,
  Gauge,
  Heart,
  TrendingUp,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";
import type React from "react";
import { startTransition, useEffect, useId, useOptimistic, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useAgentStatus } from "@/hooks/use-agent-status";
import { useAgentStatusWebSocket } from "@/hooks/use-agent-status-websocket";
import { ConnectionStatus } from "../../shared/connection-status";

/** Interface for agent metrics */
interface AgentMetrics {
  id: string;
  name: string;
  status: "active" | "idle" | "error" | "maintenance";
  healthScore: number;
  cpuUsage: number;
  memoryUsage: number;
  tokensProcessed: number;
  averageResponseTime: number;
  errorRate: number;
  uptime: number;
  tasksQueued: number;
  lastUpdate: Date;
}

/** Interface for a predictive indicator */
interface PredictiveIndicator {
  metric: string;
  current: number;
  predicted: number;
  confidence: number;
  trend: "up" | "down" | "stable";
  timeHorizon: string;
}

/** Interface for the AgentStatusDashboard component props */
interface AgentStatusDashboardProps {
  agents: AgentMetrics[];
  onAgentSelect?: (agentId: string) => void;
  refreshInterval?: number;
}

/** Function to generate mock time series data */
const GenerateMockTimeSeriesData = () => {
  return Array.from({ length: 30 }, (_, i) => ({
    errorRate: Math.random() * 5,
    responseTime: Math.random() * 100 + 50,
    time: new Date(Date.now() - (29 - i) * 60000).toLocaleTimeString("en-US", {
      hour: "2-digit",
      hour12: false,
      minute: "2-digit",
    }),
    tokensPerSecond: Math.random() * 1000 + 500,
  }));
};

/** Mock predictive indicators for testing */
const PredictiveIndicators: PredictiveIndicator[] = [
  {
    confidence: 0.89,
    current: 125,
    metric: "Response Time",
    predicted: 145,
    timeHorizon: "72h",
    trend: "up",
  },
  {
    confidence: 0.76,
    current: 2.1,
    metric: "Error Rate",
    predicted: 1.8,
    timeHorizon: "72h",
    trend: "down",
  },
  {
    confidence: 0.92,
    current: 68,
    metric: "Resource Usage",
    predicted: 72,
    timeHorizon: "72h",
    trend: "up",
  },
];

/** Function to get the status color for an agent */
// const getStatusColor = (status: AgentMetrics["status"]) => { // Future implementation
//   switch (status) {
//     case "active":
//       return "bg-green-500";
//     case "idle":
//       return "bg-yellow-500";
//     case "error":
//       return "bg-red-500";
//     case "maintenance":
//       return "bg-blue-500";
//     default:
//       return "bg-gray-500";
//   }
// };

/** Function to get the status icon for an agent */
const GetStatusIcon = (status: AgentMetrics["status"]) => {
  switch (status) {
    case "active":
      return <CheckCircle className="h-4 w-4" />;
    case "idle":
      return <Clock className="h-4 w-4" />;
    case "error":
      return <AlertTriangle className="h-4 w-4" />;
    case "maintenance":
      return <Gauge className="h-4 w-4" />;
    default:
      return <Activity className="h-4 w-4" />;
  }
};

/** Component for an agent health indicator */
const AgentHealthIndicator: React.FC<{ agent: AgentMetrics }> = ({ agent }) => {
  const healthColorClass =
    agent.healthScore >= 90
      ? "from-green-400 to-green-600"
      : agent.healthScore >= 70
        ? "from-yellow-400 to-yellow-600"
        : "from-red-400 to-red-600";

  return (
    <div className="relative">
      <div
        className={`w-16 h-16 rounded-full bg-linear-to-br ${healthColorClass} flex items-center justify-center shadow-lg`}
        style={{
          animation:
            agent.status === "active"
              ? "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite"
              : "none",
        }}
      >
        <Heart className="h-6 w-6 text-white" />
      </div>
      <div className="absolute -bottom-1 -right-1 text-xs font-bold text-white bg-black/75 rounded-full px-1.5 py-0.5">
        {agent.healthScore}%
      </div>
    </div>
  );
};

/** Component for a predictive card */
const PredictiveCard: React.FC<{ indicator: PredictiveIndicator }> = ({
  indicator,
}) => {
  const getTrendIcon = () => {
    switch (indicator.trend) {
      case "up":
        return <TrendingUp className="h-4 w-4 text-red-500" />;
      case "down":
        return <TrendingUp className="h-4 w-4 text-green-500 rotate-180" />;
      default:
        return <Activity className="h-4 w-4 text-blue-500" />;
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium">{indicator.metric}</h4>
        {getTrendIcon()}
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Current:</span>
          <span className="font-medium">
            {indicator.current}
            {indicator.metric === "Response Time"
              ? "ms"
              : indicator.metric === "Error Rate"
                ? "%"
                : "%"}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Predicted ({indicator.timeHorizon}):</span>
          <span className="font-medium">
            {indicator.predicted}
            {indicator.metric === "Response Time"
              ? "ms"
              : indicator.metric === "Error Rate"
                ? "%"
                : "%"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Progress value={indicator.confidence * 100} className="flex-1" />
          <span className="text-xs text-gray-500">
            {Math.round(indicator.confidence * 100)}%
          </span>
        </div>
      </div>
    </Card>
  );
};

/** Component for the AgentStatusDashboard */
export const AgentStatusDashboard: React.FC<AgentStatusDashboardProps> = ({
  agents: externalAgents,
  onAgentSelect,
  refreshInterval: _refreshInterval = 5000,
}) => {
  // Avoid rendering SVG gradient defs in test environment to prevent React/JSDOM warnings
  const isTestEnv = typeof process !== "undefined" && process.env.NODE_ENV === "test";
  /** Response time gradient ID */
  const responseTimeGradientId = useId();
  /** Time series data */
  const [timeSeriesData] = useState(GenerateMockTimeSeriesData);
  /** Selected agent */
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  /** Last update time */
  const [lastUpdateTime, setLastUpdateTime] = useState<string>("");
  /** Is client */
  const [isClient, setIsClient] = useState(false);

  // Use WebSocket for real-time agent status updates
  const {
    isConnected,
    connectionError,
    reconnectAttempts,
    connect,
    disconnect: _disconnect,
    startAgentMonitoring: _startAgentMonitoring,
    stopAgentMonitoring: _stopAgentMonitoring,
  } = useAgentStatusWebSocket();

  // Use agent status store
  const {
    agents: storeAgents,
    activeAgents: _activeAgents,
    currentSession: _currentSession,
    isMonitoring,
    error,
    startMonitoring,
    stopMonitoring,
  } = useAgentStatus();

  // Convert store agents to metrics format
  const agents: AgentMetrics[] = storeAgents.map((agent) => ({
    averageResponseTime: 100,
    cpuUsage: Math.random() * 100, // TODO: Get from resource usage
    errorRate: agent.status === "error" ? 15 : 2,
    healthScore: agent.progress || 75,
    id: agent.id,
    lastUpdate: new Date(agent.updatedAt),
    memoryUsage: Math.random() * 100, // TODO: Get from resource usage
    name: agent.name,
    status:
      agent.status === "executing" || agent.status === "thinking"
        ? "active"
        : agent.status === "idle" || agent.status === "initializing"
          ? "idle"
          : agent.status === "error"
            ? "error"
            : "idle",
    tasksQueued: agent.tasks?.filter((t) => t.status === "pending").length || 0,
    tokensProcessed: 0, // TODO: Get from resource usage
    uptime: 3600,
  }));

  // Using React 19's useOptimistic for immediate UI updates
  const [optimisticAgents, updateOptimisticAgents] = useOptimistic(
    agents.length > 0 ? agents : externalAgents || [],
    (_state, newAgents: AgentMetrics[]) => newAgents
  );

  // Fix hydration mismatch by ensuring client-side rendering for time
  useEffect(() => {
    setIsClient(true);
    setLastUpdateTime(new Date().toLocaleTimeString());
  }, []);

  // Update optimistic agents when store agents change
  useEffect(() => {
    if (agents.length > 0) {
      startTransition(() => {
        updateOptimisticAgents(agents);
        setLastUpdateTime(new Date().toLocaleTimeString());
      });
    }
  }, [agents, updateOptimisticAgents]);

  const totalActiveAgents = optimisticAgents.filter(
    (a) => a.status === "active"
  ).length;
  const averageHealthScore =
    optimisticAgents.reduce((sum, a) => sum + a.healthScore, 0) /
    optimisticAgents.length;
  const totalTasksQueued = optimisticAgents.reduce((sum, a) => sum + a.tasksQueued, 0);

  return (
    <div className="space-y-6 p-6">
      {/* WebSocket Connection Status */}
      <ConnectionStatus
        status={isConnected ? "connected" : connectionError ? "error" : "disconnected"}
        onReconnect={connect}
        variant="compact"
        className="mb-4"
      />

      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agent Status Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time monitoring and predictive analytics
          </p>
        </div>
        <div className="flex items-center gap-4">
          {isMonitoring ? (
            <Button
              onClick={stopMonitoring}
              variant="outline"
              className="flex items-center gap-2"
            >
              <WifiOff className="h-4 w-4" />
              Stop Monitoring
            </Button>
          ) : (
            <Button
              onClick={startMonitoring}
              disabled={!isConnected}
              className="flex items-center gap-2"
            >
              <Wifi className="h-4 w-4" />
              Start Monitoring
            </Button>
          )}
          <Badge
            variant={isConnected ? "default" : "secondary"}
            className="flex items-center gap-2"
          >
            <div
              className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500 animate-pulse" : "bg-gray-500"}`}
            />
            {isConnected ? "Live Updates" : "Disconnected"}
          </Badge>
          <span className="text-sm text-gray-500">
            Last updated: {isClient ? lastUpdateTime : "--:--:--"}
          </span>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{totalActiveAgents}</div>
            <p className="text-xs text-muted-foreground">
              of {optimisticAgents.length} total agents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Health</CardTitle>
            <Heart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(averageHealthScore)}%</div>
            <p className="text-xs text-muted-foreground">Across all agents</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks Queued</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTasksQueued}</div>
            <p className="text-xs text-muted-foreground">Pending processing</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Load</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">68%</div>
            <p className="text-xs text-muted-foreground">Resource utilization</p>
          </CardContent>
        </Card>
      </div>

      {/* Agent Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Agent Status Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {optimisticAgents.map((agent) => (
                <motion.div
                  key={agent.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    selectedAgent === agent.id
                      ? "ring-2 ring-blue-500 bg-blue-50"
                      : "hover:shadow-md"
                  }`}
                  onClick={() => {
                    setSelectedAgent(agent.id);
                    onAgentSelect?.(agent.id);
                  }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <AgentHealthIndicator agent={agent} />
                      <div>
                        <h3 className="font-semibold">{agent.name}</h3>
                        <Badge
                          variant={agent.status === "active" ? "default" : "secondary"}
                          className="flex items-center gap-1"
                        >
                          {GetStatusIcon(agent.status)}
                          {agent.status}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">CPU</span>
                      <div className="flex items-center gap-2">
                        <Progress value={agent.cpuUsage} className="w-16" />
                        <span className="text-sm font-medium">{agent.cpuUsage}%</span>
                      </div>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Memory</span>
                      <div className="flex items-center gap-2">
                        <Progress value={agent.memoryUsage} className="w-16" />
                        <span className="text-sm font-medium">
                          {agent.memoryUsage}%
                        </span>
                      </div>
                    </div>

                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Response Time</span>
                      <span className="font-medium">{agent.averageResponseTime}ms</span>
                    </div>

                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Tasks Queued</span>
                      <span className="font-medium">{agent.tasksQueued}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </CardContent>
      </Card>

      {/* Predictive Analytics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Predictive Analytics (72h Horizon)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {PredictiveIndicators.map((indicator, index) => (
              <PredictiveCard
                key={`predictive-${indicator.metric}-${index}`}
                indicator={indicator}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Performance Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Response Time Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={timeSeriesData}>
                {isClient && !isTestEnv && (
                  <defs>
                    <linearGradient
                      id={responseTimeGradientId}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
                    </linearGradient>
                  </defs>
                )}
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="responseTime"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill={
                    isClient && !isTestEnv
                      ? `url(#${responseTimeGradientId})`
                      : "#3b82f6"
                  }
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Token Processing Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeSeriesData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="tokensPerSecond"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ fill: "#10b981", r: 4, strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Section */}
      <div className="space-y-3">
        {connectionError && (
          <Alert className="border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              WebSocket connection error: {connectionError}
              {reconnectAttempts > 0 && ` (Reconnect attempt ${reconnectAttempts}/5)`}
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert className="border-orange-200 bg-orange-50">
            <AlertTriangle className="h-4 w-4 text-orange-600" />
            <AlertDescription className="text-orange-800">
              Agent monitoring error: {error}
            </AlertDescription>
          </Alert>
        )}

        {optimisticAgents.some((a) => a.status === "error") && (
          <Alert className="border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {optimisticAgents.filter((a) => a.status === "error").length} agent(s) are
              experiencing errors and require attention.
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  );
};

export default AgentStatusDashboard;
