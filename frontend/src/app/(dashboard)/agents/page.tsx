/**
 * @fileoverview Agent monitoring dashboard page component.
 *
 * Provides a comprehensive interface for monitoring AI agent performance,
 * collaboration, and network connectivity in the TripSage platform. Features
 * real-time metrics, agent status tracking, and collaborative agent management
 * with WebSocket integration for live updates.
 */

"use client";

import { Activity, Brain, Network, Settings, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import {
  AgentCollaborationHub,
  AgentStatusDashboard,
  type ConnectionAnalytics,
  ConnectionStatus,
  type NetworkMetrics,
  useWebSocketAgent,
} from "@/components/features/agent-monitoring";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Mock data for demonstration
const MOCK_AGENT_METRICS = [
  {
    averageResponseTime: 125,
    cpuUsage: 68,
    errorRate: 0.8,
    healthScore: 94,
    id: "agent-1",
    lastUpdate: new Date(),
    memoryUsage: 45,
    name: "Research Agent",
    status: "active" as const,
    tasksQueued: 3,
    tokensProcessed: 15420,
    uptime: 98.5,
  },
  {
    averageResponseTime: 156,
    cpuUsage: 78,
    errorRate: 1.2,
    healthScore: 87,
    id: "agent-2",
    lastUpdate: new Date(),
    memoryUsage: 62,
    name: "Planning Agent",
    status: "active" as const,
    tasksQueued: 5,
    tokensProcessed: 12890,
    uptime: 97.2,
  },
  {
    averageResponseTime: 98,
    cpuUsage: 25,
    errorRate: 0.5,
    healthScore: 92,
    id: "agent-3",
    lastUpdate: new Date(),
    memoryUsage: 38,
    name: "Booking Agent",
    status: "idle" as const,
    tasksQueued: 1,
    tokensProcessed: 8750,
    uptime: 99.1,
  },
  {
    averageResponseTime: 142,
    cpuUsage: 55,
    errorRate: 1.5,
    healthScore: 89,
    id: "agent-4",
    lastUpdate: new Date(),
    memoryUsage: 51,
    name: "Support Agent",
    status: "active" as const,
    tasksQueued: 2,
    tokensProcessed: 11200,
    uptime: 96.8,
  },
];

const MOCK_NETWORK_METRICS: NetworkMetrics = {
  bandwidth: 15600000, // 15.6 MB/s
  jitter: 5,
  latency: 87,
  packetLoss: 0.2,
  quality: "excellent",
  signalStrength: 92,
};

const MOCK_CONNECTION_ANALYTICS: ConnectionAnalytics = {
  avgResponseTime: 125,
  connectionTime: 45000,
  failedMessages: 3,
  reconnectCount: 0,
  totalMessages: 1247,
  uptime: 3600,
};

/**
 * Agent monitoring dashboard page component.
 *
 * Renders a comprehensive dashboard for monitoring AI agent performance and
 * collaboration in the TripSage platform. Displays real-time metrics including
 * agent health scores, network connectivity, and collaborative task management.
 *
 * Features:
 * - Real-time agent status monitoring with health scores and performance metrics
 * - Network connectivity diagnostics with WebSocket status
 * - Agent collaboration hub for task coordination
 * - Tabbed interface for overview, collaboration, network, and settings views
 * - Responsive design with mobile-friendly layouts
 *
 * @returns {JSX.Element} The rendered agent monitoring dashboard page.
 */
export default function AgentsPage() {
  const [selectedTab, setSelectedTab] = useState("overview");
  const [_selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // WebSocket connection for real-time updates (disabled in development)
  const { isConnected, connect, disconnect, reconnectAttempts } = useWebSocketAgent();

  // Handle real-time message updates
  useEffect(() => {
    // Real-time updates handled within the hook's internal store.
  }, []);

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgent(agentId);
    // Selection side effects can broadcast via Supabase in future iterations.
  };

  const handleOptimizeConnection = () => {
    // Placeholder for future optimization broadcast.
  };

  const activeAgents = MOCK_AGENT_METRICS.filter((a) => a.status === "active").length;
  const averageHealth =
    MOCK_AGENT_METRICS.reduce((sum, a) => sum + a.healthScore, 0) /
    MOCK_AGENT_METRICS.length;
  const totalTasks = MOCK_AGENT_METRICS.reduce((sum, a) => sum + a.tasksQueued, 0);

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Agent Monitoring</h1>
          <p className="text-gray-600 mt-2">
            Real-time AI agent performance and collaboration monitoring
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ConnectionStatus
            status={isConnected ? "connected" : "disconnected"}
            metrics={MOCK_NETWORK_METRICS}
            analytics={MOCK_CONNECTION_ANALYTICS}
            onReconnect={connect}
            onOptimize={handleOptimizeConnection}
            variant="compact"
          />
          <Button
            variant="outline"
            onClick={() => disconnect()}
            disabled={!isConnected}
          >
            Disconnect
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{activeAgents}</div>
            <p className="text-xs text-muted-foreground">
              of {MOCK_AGENT_METRICS.length} total agents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Health</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(averageHealth)}%</div>
            <p className="text-xs text-muted-foreground">System performance</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks Queued</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTasks}</div>
            <p className="text-xs text-muted-foreground">Pending processing</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connection Quality</CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{MOCK_NETWORK_METRICS.quality}</div>
            <p className="text-xs text-muted-foreground">
              {MOCK_NETWORK_METRICS.latency}ms latency
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="collaboration" className="flex items-center gap-2">
            <Brain className="h-4 w-4" />
            Collaboration
          </TabsTrigger>
          <TabsTrigger value="network" className="flex items-center gap-2">
            <Network className="h-4 w-4" />
            Network
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <AgentStatusDashboard
            agents={MOCK_AGENT_METRICS}
            onAgentSelect={handleAgentSelect}
            refreshInterval={3000}
          />
        </TabsContent>

        <TabsContent value="collaboration" className="space-y-6">
          <AgentCollaborationHub
            agents={MOCK_AGENT_METRICS.map((agent) => ({
              currentTask: agent.status === "active" ? "Processing request" : undefined,
              id: agent.id,
              lastActive: agent.lastUpdate,
              name: agent.name,
              performance: {
                accuracy: Math.round(agent.healthScore * 0.9),
                efficiency: Math.round(agent.healthScore * 0.95),
                speed: Math.round(100 - agent.averageResponseTime / 2),
              },
              specialization: agent.name.includes("Research")
                ? "Data Analysis"
                : agent.name.includes("Planning")
                  ? "Trip Planning"
                  : agent.name.includes("Booking")
                    ? "Reservations"
                    : "Customer Service",
              status: agent.status,
              workload: agent.cpuUsage,
            }))}
            handoffs={[]}
            onAgentSelect={handleAgentSelect}
          />
        </TabsContent>

        <TabsContent value="network" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ConnectionStatus
              status={isConnected ? "connected" : "disconnected"}
              metrics={MOCK_NETWORK_METRICS}
              analytics={MOCK_CONNECTION_ANALYTICS}
              onReconnect={connect}
              onOptimize={handleOptimizeConnection}
              showMetrics
              showOptimizations
            />

            <Card>
              <CardHeader>
                <CardTitle>Realtime Diagnostics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Status:</span>
                    <Badge variant="outline" className="ml-2">
                      {isConnected ? "connected" : "disconnected"}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Reconnects:</span>
                    <span className="ml-2 font-medium">{reconnectAttempts}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="settings" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Agent Monitoring Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="text-center py-8">
                  <Settings className="h-12 w-12 mx-auto text-gray-400 mb-2" />
                  <p className="text-gray-600">Settings panel coming soon</p>
                  <p className="text-sm text-gray-500">
                    Configure monitoring preferences and alerts
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
