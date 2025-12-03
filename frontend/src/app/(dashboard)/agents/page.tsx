/**
 * @fileoverview Agent monitoring dashboard page component powered by the shared
 * agent status store and realtime hook.
 */

"use client";

import { ActivityIcon, BrainIcon, NetworkIcon, ZapIcon } from "lucide-react";
import { useMemo } from "react";
import { AgentStatusDashboard } from "@/components/features/agent-monitoring/dashboard/agent-status-dashboard";
import { ConnectionStatus } from "@/components/features/shared/connection-status";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAgentStatusWebSocket } from "@/hooks/chat/use-agent-status-websocket";
import { useAgentStatusStore } from "@/stores/agent-status-store";

/**
 * Renders the agent monitoring dashboard with realtime controls and metrics.
 *
 * @returns Agent monitoring layout with connection controls and dashboard
 * widgets.
 */
export default function AgentsPage() {
  const { connectionStatus, connectionError, pause, reconnect, resume, retryCount } =
    useAgentStatusWebSocket();
  const agents = useAgentStatusStore((state) => state.agents);
  const activeAgents = useAgentStatusStore((state) => state.activeAgents.length);

  const [averageHealth, pendingTasks] = useMemo(() => {
    if (agents.length === 0) {
      return [0, 0];
    }
    const healthSum = agents.reduce((sum, agent) => sum + (agent.progress ?? 0), 0);
    const pendingTotal = agents.reduce(
      (sum, agent) =>
        sum + agent.tasks.filter((task) => task.status === "pending").length,
      0
    );
    return [Math.round(healthSum / agents.length), pendingTotal];
  }, [agents]);

  const isConnected = connectionStatus === "subscribed";
  const connectionLabel = isConnected ? "connected" : "disconnected";

  const toggleRealtime = () => {
    if (isConnected) {
      pause();
      return;
    }
    resume();
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Agent Monitoring</h1>
          <p className="text-gray-600 mt-2">
            Live visibility into agent execution, status transitions, and realtime
            health.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ConnectionStatus
            status={
              isConnected
                ? "connected"
                : connectionStatus === "error"
                  ? "error"
                  : "disconnected"
            }
            analytics={{
              avgResponseTime: 0,
              connectionTime: 0,
              failedMessages: 0,
              reconnectCount: retryCount,
              totalMessages: 0,
              uptime: 0,
            }}
            onReconnect={reconnect}
            variant="compact"
            showMetrics={false}
          />
          <Button variant="outline" onClick={toggleRealtime}>
            {isConnected ? "Pause Realtime" : "Resume Realtime"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <ActivityIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{activeAgents}</div>
            <p className="text-xs text-muted-foreground">
              of {agents.length} tracked agents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Health</CardTitle>
            <BrainIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{averageHealth}%</div>
            <p className="text-xs text-muted-foreground">
              Progress across active agents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks Queued</CardTitle>
            <ZapIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingTasks}</div>
            <p className="text-xs text-muted-foreground">Pending task executions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connection State</CardTitle>
            <NetworkIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{connectionLabel}</div>
            {connectionError ? (
              <p className="text-xs text-red-600">{connectionError}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                Reconnect attempts: {retryCount}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">
            Agent Status Dashboard
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <AgentStatusDashboard
            connectionStatus={connectionStatus}
            connectionError={connectionError}
            pause={pause}
            reconnect={reconnect}
            retryCount={retryCount}
            resume={resume}
          />
        </CardContent>
      </Card>
    </div>
  );
}
