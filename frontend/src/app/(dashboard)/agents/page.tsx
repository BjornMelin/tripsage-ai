"use client";

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
import { Activity, Brain, Network, Settings, Zap } from "lucide-react";
import { useEffect, useState } from "react";

// Mock data for demonstration
const mockAgentMetrics = [
  {
    id: "agent-1",
    name: "Research Agent",
    status: "active" as const,
    healthScore: 94,
    cpuUsage: 68,
    memoryUsage: 45,
    tokensProcessed: 15420,
    averageResponseTime: 125,
    errorRate: 0.8,
    uptime: 98.5,
    tasksQueued: 3,
    lastUpdate: new Date(),
  },
  {
    id: "agent-2",
    name: "Planning Agent",
    status: "active" as const,
    healthScore: 87,
    cpuUsage: 78,
    memoryUsage: 62,
    tokensProcessed: 12890,
    averageResponseTime: 156,
    errorRate: 1.2,
    uptime: 97.2,
    tasksQueued: 5,
    lastUpdate: new Date(),
  },
  {
    id: "agent-3",
    name: "Booking Agent",
    status: "idle" as const,
    healthScore: 92,
    cpuUsage: 25,
    memoryUsage: 38,
    tokensProcessed: 8750,
    averageResponseTime: 98,
    errorRate: 0.5,
    uptime: 99.1,
    tasksQueued: 1,
    lastUpdate: new Date(),
  },
  {
    id: "agent-4",
    name: "Support Agent",
    status: "active" as const,
    healthScore: 89,
    cpuUsage: 55,
    memoryUsage: 51,
    tokensProcessed: 11200,
    averageResponseTime: 142,
    errorRate: 1.5,
    uptime: 96.8,
    tasksQueued: 2,
    lastUpdate: new Date(),
  },
];

const mockNetworkMetrics: NetworkMetrics = {
  latency: 87,
  bandwidth: 15600000, // 15.6 MB/s
  packetLoss: 0.2,
  jitter: 5,
  quality: "excellent",
  signalStrength: 92,
};

const mockConnectionAnalytics: ConnectionAnalytics = {
  connectionTime: 45000,
  reconnectCount: 0,
  totalMessages: 1247,
  failedMessages: 3,
  avgResponseTime: 125,
  uptime: 3600,
};

export default function AgentsPage() {
  const [selectedTab, setSelectedTab] = useState("overview");
  const [_selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // WebSocket connection for real-time updates (disabled in development)
  const {
    connectionStatus,
    lastMessage,
    sendMessage,
    isConnected,
    reconnectCount,
    queuedMessages,
    connect,
    disconnect,
  } = useWebSocketAgent({
    url: process.env.NEXT_PUBLIC_WS_URL || "", // Disable WebSocket in development
    reconnectInterval: 2000,
    maxReconnectAttempts: 0, // Disable reconnection attempts
    heartbeatInterval: 30000,
  });

  // Handle real-time message updates
  useEffect(() => {
    if (lastMessage) {
      console.log("Received agent update:", lastMessage);
      // Here you would typically update your agent data based on the message
    }
  }, [lastMessage]);

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgent(agentId);
    // Send agent selection message
    sendMessage({
      type: "agent_select",
      data: { agentId },
    });
  };

  const handleOptimizeConnection = () => {
    sendMessage({
      type: "optimize_connection",
      data: { timestamp: Date.now() },
    });
  };

  const activeAgents = mockAgentMetrics.filter((a) => a.status === "active").length;
  const averageHealth =
    mockAgentMetrics.reduce((sum, a) => sum + a.healthScore, 0) /
    mockAgentMetrics.length;
  const totalTasks = mockAgentMetrics.reduce((sum, a) => sum + a.tasksQueued, 0);

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
            status={connectionStatus}
            metrics={mockNetworkMetrics}
            analytics={mockConnectionAnalytics}
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
              of {mockAgentMetrics.length} total agents
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
            <div className="text-2xl font-bold">{mockNetworkMetrics.quality}</div>
            <p className="text-xs text-muted-foreground">
              {mockNetworkMetrics.latency}ms latency
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
            agents={mockAgentMetrics}
            onAgentSelect={handleAgentSelect}
            refreshInterval={3000}
          />
        </TabsContent>

        <TabsContent value="collaboration" className="space-y-6">
          <AgentCollaborationHub
            agents={mockAgentMetrics.map((agent) => ({
              id: agent.id,
              name: agent.name,
              status: agent.status,
              specialization: agent.name.includes("Research")
                ? "Data Analysis"
                : agent.name.includes("Planning")
                  ? "Trip Planning"
                  : agent.name.includes("Booking")
                    ? "Reservations"
                    : "Customer Service",
              currentTask: agent.status === "active" ? "Processing request" : undefined,
              performance: {
                accuracy: Math.round(agent.healthScore * 0.9),
                speed: Math.round(100 - agent.averageResponseTime / 2),
                efficiency: Math.round(agent.healthScore * 0.95),
              },
              workload: agent.cpuUsage,
              lastActive: agent.lastUpdate,
            }))}
            handoffs={[]}
            onAgentSelect={handleAgentSelect}
          />
        </TabsContent>

        <TabsContent value="network" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ConnectionStatus
              status={connectionStatus}
              metrics={mockNetworkMetrics}
              analytics={mockConnectionAnalytics}
              onReconnect={connect}
              onOptimize={handleOptimizeConnection}
              showMetrics
              showOptimizations
            />

            <Card>
              <CardHeader>
                <CardTitle>WebSocket Diagnostics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Status:</span>
                    <Badge variant="outline" className="ml-2">
                      {connectionStatus}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Reconnects:</span>
                    <span className="ml-2 font-medium">{reconnectCount}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Queued Messages:</span>
                    <span className="ml-2 font-medium">{queuedMessages}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Last Message:</span>
                    <span className="ml-2 font-medium">
                      {lastMessage
                        ? new Date(lastMessage.timestamp).toLocaleTimeString()
                        : "None"}
                    </span>
                  </div>
                </div>

                {lastMessage && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <div className="text-sm">
                      <strong>Last Message:</strong>
                      <pre className="mt-1 text-xs text-gray-600 overflow-auto">
                        {JSON.stringify(lastMessage, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
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
