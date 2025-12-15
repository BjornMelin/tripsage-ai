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
import { cn } from "@/lib/utils";
import { useAgentStatusStore } from "@/stores/agent-status-store";

/**
 * Agent dashboard colors aligned with statusVariants.
 * Active states use green (aligned with urgency.low/status.active),
 * errors use red (aligned with urgency.high/status.error).
 */
const AGENT_COLORS = {
  active: "text-green-700",
  error: "text-red-700",
} as const;

/** Unified connection status for UI state management. */
type AgentConnectionStatus = "connected" | "disconnected" | "error";

/** Button labels mapped to each connection status. */
const REALTIME_BUTTON_LABEL: Record<AgentConnectionStatus, string> = {
  connected: "Pause Realtime",
  disconnected: "Resume Realtime",
  error: "Reconnect",
} as const;

/**
 * Derives unified connection status from websocket state.
 *
 * @param isConnected - Whether websocket is actively subscribed
 * @param connectionStatus - Raw connection status from websocket hook
 * @returns Unified status for UI consumption
 */
function getConnectionStatus(
  isConnected: boolean,
  connectionStatus: "subscribed" | "error" | "disconnected" | (string & {})
): AgentConnectionStatus {
  if (isConnected) return "connected";
  if (connectionStatus === "error") return "error";
  return "disconnected";
}

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

  const [averageProgress, pendingTasks] = useMemo(() => {
    if (agents.length === 0) {
      return [0, 0];
    }
    const progressSum = agents.reduce((sum, agent) => sum + (agent.progress ?? 0), 0);
    const pendingTotal = agents.reduce(
      (sum, agent) =>
        sum + agent.tasks.filter((task) => task.status === "pending").length,
      0
    );
    return [Math.round(progressSum / agents.length), pendingTotal];
  }, [agents]);

  const isConnected = connectionStatus === "subscribed";
  const connectionLabel = isConnected ? "connected" : "disconnected";
  const computedConnectionStatus = getConnectionStatus(isConnected, connectionStatus);

  const toggleRealtime = () => {
    if (computedConnectionStatus === "connected") {
      pause();
      return;
    }
    if (computedConnectionStatus === "error") {
      reconnect();
      return;
    }
    resume();
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold">Agent Monitoring</h1>
          <p className="text-muted-foreground mt-2">
            Live visibility into agent execution, status transitions, and realtime
            health.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ConnectionStatus
            status={computedConnectionStatus}
            onReconnect={reconnect}
            variant="compact"
            showMetrics={false}
          />
          <Button variant="outline" onClick={toggleRealtime}>
            {REALTIME_BUTTON_LABEL[computedConnectionStatus]}
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
            <div className={cn("text-2xl font-bold", AGENT_COLORS.active)}>
              {activeAgents}
            </div>
            <p className="text-xs text-muted-foreground">
              of {agents.length} tracked agents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Progress</CardTitle>
            <BrainIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{averageProgress}%</div>
            <p className="text-xs text-muted-foreground">
              Reported progress across active agents
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
              <p className={cn("text-xs", AGENT_COLORS.error)}>{connectionError}</p>
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
