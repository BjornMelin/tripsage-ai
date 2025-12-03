/**
 * @fileoverview Deterministic agent monitoring dashboard backed by the
 * `useAgentStatusStore` + `useAgentStatusWebSocket` pair.
 */

"use client";

import type { AgentStatusType } from "@schemas/agent-status";
import {
  ActivityIcon,
  AlertTriangleIcon,
  CpuIcon,
  GaugeCircleIcon,
  PauseCircleIcon,
  PlayCircleIcon,
  RefreshCwIcon,
  UsersIcon,
} from "lucide-react";
import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { AgentStatusRealtimeControls } from "@/hooks/chat/use-agent-status-websocket";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import { ConnectionStatus } from "../../shared/connection-status";

type AgentStatusDashboardProps = Pick<
  AgentStatusRealtimeControls,
  | "connectionStatus"
  | "connectionError"
  | "retryCount"
  | "resume"
  | "pause"
  | "reconnect"
>;

function FormatTimestamp(timestamp: string | null) {
  if (!timestamp) {
    return "—";
  }
  try {
    return new Intl.DateTimeFormat("en", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(timestamp));
  } catch {
    return timestamp;
  }
}

function DeriveConnectionBadge(status: string): { color: string; label: string } {
  switch (status) {
    case "subscribed":
      return { color: "bg-green-500", label: "Connected" };
    case "connecting":
      return { color: "bg-yellow-500", label: "Connecting" };
    case "error":
      return { color: "bg-red-500", label: "Error" };
    default:
      return { color: "bg-gray-400", label: "Idle" };
  }
}

/**
 * Renders the realtime agent status dashboard fed by Zustand + WebSocket data.
 *
 * @returns Monitoring layout with status cards and activity feed.
 */
export const AgentStatusDashboard = ({
  connectionStatus,
  connectionError,
  pause,
  reconnect,
  retryCount,
  resume,
}: AgentStatusDashboardProps) => {
  const agents = useAgentStatusStore((state) => state.agents);
  const activeAgents = useAgentStatusStore((state) => state.activeAgents);
  const activities = useAgentStatusStore((state) =>
    state.activities.slice(-6).reverse()
  );
  const resourceUsage = useAgentStatusStore((state) =>
    state.resourceUsage.slice(-5).reverse()
  );
  const isMonitoring = useAgentStatusStore((state) => state.isMonitoring);
  const lastEventAt = useAgentStatusStore((state) => state.lastEventAt);

  const summary = useMemo(() => {
    if (!agents.length) {
      return {
        averageProgress: 0,
        inProgressTasks: 0,
      };
    }
    const progressTotal = agents.reduce((total, agent) => total + agent.progress, 0);
    const inProgressTasks = agents.reduce((total, agent) => {
      const runningTasks = agent.tasks.filter(
        (task) => task.status === "in_progress"
      ).length;
      return total + runningTasks;
    }, 0);
    return {
      averageProgress: Math.round(progressTotal / agents.length),
      inProgressTasks,
    };
  }, [agents]);

  const connectionBadge = DeriveConnectionBadge(connectionStatus);

  return (
    <div className="space-y-6 p-6">
      <ConnectionStatus
        status={
          connectionStatus === "subscribed"
            ? "connected"
            : connectionStatus === "error"
              ? "error"
              : connectionStatus === "connecting"
                ? "connecting"
                : "disconnected"
        }
        onReconnect={reconnect}
        className="mb-4"
        variant="compact"
      />

      <Card>
        <CardContent className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between py-6">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              Agent Status Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Live Supabase updates. Last event: {FormatTimestamp(lastEventAt)}
            </p>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <Badge className="flex items-center gap-2 w-fit">
              <span className={`h-2 w-2 rounded-full ${connectionBadge.color}`} />
              {connectionBadge.label}
            </Badge>
            {connectionError && (
              <Badge variant="destructive" className="flex items-center gap-1">
                <AlertTriangleIcon className="h-3.5 w-3.5" />
                {connectionError}
              </Badge>
            )}
            <div className="flex gap-2">
              <Button
                onClick={isMonitoring ? pause : resume}
                variant="outline"
                className="flex items-center gap-2"
              >
                {isMonitoring ? (
                  <PauseCircleIcon className="h-4 w-4" />
                ) : (
                  <PlayCircleIcon className="h-4 w-4" />
                )}
                {isMonitoring ? "Pause" : "Resume"}
              </Button>
              <Button
                onClick={reconnect}
                variant="outline"
                className="flex items-center gap-2"
              >
                <RefreshCwIcon className="h-4 w-4" /> Reconnect
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <ActivityIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeAgents.length}</div>
            <p className="text-xs text-muted-foreground">
              of {agents.length || 0} total agents
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Progress</CardTitle>
            <GaugeCircleIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.averageProgress}%</div>
            <Progress value={summary.averageProgress} className="mt-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasks In Flight</CardTitle>
            <UsersIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.inProgressTasks}</div>
            <p className="text-xs text-muted-foreground">Active task executions</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Retry Count</CardTitle>
            <RefreshCwIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{retryCount}</div>
            <p className="text-xs text-muted-foreground">
              Exponential backoff attempts
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UsersIcon className="h-5 w-5" /> Agents
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {agents.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No agents have reported yet.
            </p>
          )}
          {agents.map((agent) => (
            <div key={agent.id} className="border rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{agent.name}</p>
                  <p className="text-sm text-muted-foreground">{agent.type}</p>
                </div>
                <Badge
                  variant={ACTIVE_STATUSES.has(agent.status) ? "default" : "secondary"}
                >
                  {agent.status}
                </Badge>
              </div>
              <Progress value={agent.progress} />
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span>Progress: {agent.progress}%</span>
                <span>Tasks: {agent.tasks.length}</span>
                <span>Current Task: {agent.currentTaskId ?? "—"}</span>
                <span>Updated: {FormatTimestamp(agent.updatedAt)}</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CpuIcon className="h-5 w-5" /> Recent Resource Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {resourceUsage.length === 0 && (
              <p className="text-muted-foreground">No samples recorded yet.</p>
            )}
            {resourceUsage.map((sample, index) => (
              <div
                key={`${sample.timestamp}-${index}`}
                className="flex items-center justify-between"
              >
                <div>
                  <p className="font-medium">{FormatTimestamp(sample.timestamp)}</p>
                  <p className="text-muted-foreground">
                    CPU {sample.cpuUsage}% · Memory {sample.memoryUsage}% · Requests{" "}
                    {sample.networkRequests}
                  </p>
                </div>
                <Badge variant="outline">{sample.activeAgents} active</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ActivityIcon className="h-5 w-5" /> Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {activities.length === 0 && (
              <p className="text-muted-foreground">No activity yet.</p>
            )}
            {activities.map((activity) => (
              <div key={activity.id} className="border rounded-md p-3">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{activity.type}</p>
                  <span className="text-xs text-muted-foreground">
                    {FormatTimestamp(activity.timestamp)}
                  </span>
                </div>
                <p className="text-muted-foreground mt-1">{activity.message}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const ACTIVE_STATUSES = new Set<AgentStatusType>([
  "initializing",
  "active",
  "waiting",
  "paused",
  "thinking",
  "executing",
]);

export default AgentStatusDashboard;
export type { AgentStatusDashboardProps };
