/**
 * @fileoverview Agent collaboration hub component for monitoring multi-agent coordination and handoffs.
 */

"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  ActivityIcon,
  AlertTriangleIcon,
  ArrowRightLeftIcon,
  BrainIcon,
  CheckCircle2Icon,
  ClockIcon,
  GitBranchIcon,
  NetworkIcon,
  TimerIcon,
  TrendingDownIcon,
  TrendingUpIcon,
  UsersIcon,
  WorkflowIcon,
} from "lucide-react";
import type React from "react";
import { startTransition, useEffect, useOptimistic, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import {
  AGENT_STATUS_COLORS,
  DEFAULT_HANDOFF_STATUS_COLOR,
  HANDOFF_STATUS_COLORS,
  TREND_COLORS,
} from "@/lib/variants/status";

/** Interface for an agent */
interface Agent {
  id: string;
  name: string;
  avatar?: string;
  status: "active" | "busy" | "idle" | "offline";
  specialization: string;
  currentTask?: string;
  performance: {
    accuracy: number;
    speed: number;
    efficiency: number;
  };
  workload: number; // 0-100
  lastActive: Date;
}

/** Interface for an agent handoff */
interface AgentHandoff {
  id: string;
  fromAgent: string;
  toAgent: string;
  task: string;
  reason: string;
  timestamp: Date;
  status: "pending" | "completed" | "failed";
  confidence: number;
}

/** Interface for a collaboration metric */
interface CollaborationMetric {
  metric: string;
  value: number;
  trend: "up" | "down" | "stable";
  description: string;
}

/** Interface for the AgentCollaborationHub component props */
interface AgentCollaborationHubProps {
  agents: Agent[];
  handoffs: AgentHandoff[];
  onAgentSelect?: (agentId: string) => void;
  onHandoffApprove?: (handoffId: string) => void;
  onHandoffReject?: (handoffId: string) => void;
  className?: string;
}

/** Mock agents for testing */
const MockAgents: Agent[] = [
  {
    avatar: "/agents/research.jpg",
    currentTask: "Market trend analysis",
    id: "agent-1",
    lastActive: new Date(),
    name: "Research Agent",
    performance: { accuracy: 94, efficiency: 91, speed: 87 },
    specialization: "Data Analysis",
    status: "active",
    workload: 75,
  },
  {
    avatar: "/agents/planning.jpg",
    currentTask: "Itinerary optimization",
    id: "agent-2",
    lastActive: new Date(Date.now() - 300000),
    name: "Planning Agent",
    performance: { accuracy: 89, efficiency: 88, speed: 92 },
    specialization: "Trip Planning",
    status: "busy",
    workload: 90,
  },
  {
    avatar: "/agents/booking.jpg",
    id: "agent-3",
    lastActive: new Date(Date.now() - 600000),
    name: "Booking Agent",
    performance: { accuracy: 96, efficiency: 93, speed: 85 },
    specialization: "Reservations",
    status: "idle",
    workload: 25,
  },
  {
    avatar: "/agents/support.jpg",
    currentTask: "Query resolution",
    id: "agent-4",
    lastActive: new Date(Date.now() - 120000),
    name: "Support Agent",
    performance: { accuracy: 92, efficiency: 90, speed: 88 },
    specialization: "Customer Service",
    status: "active",
    workload: 60,
  },
];

/** Mock handoffs for testing */
const MockHandoffs: AgentHandoff[] = [
  {
    confidence: 0.89,
    fromAgent: "agent-1",
    id: "handoff-1",
    reason: "Research completed, planning phase needed",
    status: "pending",
    task: "Create itinerary from research data",
    timestamp: new Date(),
    toAgent: "agent-2",
  },
  {
    confidence: 0.92,
    fromAgent: "agent-2",
    id: "handoff-2",
    reason: "Itinerary approved, booking required",
    status: "completed",
    task: "Book selected accommodations",
    timestamp: new Date(Date.now() - 180000),
    toAgent: "agent-3",
  },
];

/** Mock collaboration metrics for testing */
const CollaborationMetrics: CollaborationMetric[] = [
  {
    description: "Percentage of successful agent handoffs",
    metric: "Handoff Success Rate",
    trend: "up",
    value: 94,
  },
  {
    description: "Average time to complete collaborative tasks",
    metric: "Task Completion Time",
    trend: "up",
    value: 87,
  },
  {
    description: "Overall agent workload distribution",
    metric: "Agent Utilization",
    trend: "stable",
    value: 73,
  },
  {
    description: "How well agents work together",
    metric: "Coordination Efficiency",
    trend: "up",
    value: 91,
  },
];

const STATUS_ICON_CLASS = "h-3 w-3";

const AGENT_STATUS_ICONS: Record<
  Agent["status"] | "unknown",
  React.ComponentType<{ className?: string }>
> = {
  active: CheckCircle2Icon,
  busy: ClockIcon,
  idle: TimerIcon,
  offline: AlertTriangleIcon,
  unknown: ActivityIcon,
};

/** Function to get the status color for an agent */
const GetStatusColor = (status: Agent["status"]) => {
  return AGENT_STATUS_COLORS[status] ?? AGENT_STATUS_COLORS.offline;
};

/** Function to get the status icon for an agent */
const GetStatusIcon = (status: Agent["status"] | "unknown") => {
  const Icon = AGENT_STATUS_ICONS[status] ?? AGENT_STATUS_ICONS.unknown;
  return <Icon className={STATUS_ICON_CLASS} />;
};

const AgentStatusIndicator: React.FC<{ status: Agent["status"] }> = ({ status }) => (
  <div
    className={cn(
      "absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-white flex items-center justify-center",
      GetStatusColor(status)
    )}
  >
    <div className="text-white">{GetStatusIcon(status || "unknown")}</div>
  </div>
);

/** Component for an agent card */
const AgentCard: React.FC<{
  agent: Agent;
  onSelect?: (agentId: string) => void;
  isSelected?: boolean;
}> = ({ agent, onSelect, isSelected }) => {
  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase();
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "p-4 border rounded-lg cursor-pointer transition-all duration-200",
        isSelected ? "ring-2 ring-blue-500 bg-blue-50" : "hover:shadow-md"
      )}
      onClick={() => onSelect?.(agent.id)}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="relative">
          <Avatar className="h-10 w-10">
            <AvatarImage src={agent.avatar} alt={agent.name} />
            <AvatarFallback className="text-sm font-medium">
              {getInitials(agent.name)}
            </AvatarFallback>
          </Avatar>
          <AgentStatusIndicator status={agent.status} />
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">{agent.name}</h3>
          <p className="text-xs text-muted-foreground truncate">
            {agent.specialization}
          </p>
        </div>
      </div>

      {agent.currentTask && (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1">Current Task:</p>
          <p className="text-sm font-medium truncate">{agent.currentTask}</p>
        </div>
      )}

      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-xs text-muted-foreground">Workload</span>
          <span className="text-xs font-medium">{agent.workload}%</span>
        </div>
        <Progress value={agent.workload} className="h-1.5" />
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="text-xs font-medium">{agent.performance.accuracy}%</div>
                <div className="text-xs text-muted-foreground">Accuracy</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>Task accuracy rate</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="text-xs font-medium">{agent.performance.speed}%</div>
                <div className="text-xs text-muted-foreground">Speed</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>Task completion speed</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="text-xs font-medium">
                  {agent.performance.efficiency}%
                </div>
                <div className="text-xs text-muted-foreground">Efficiency</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>Resource efficiency</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </motion.div>
  );
};

/** Component for a handoff card */
const HandoffCard: React.FC<{
  handoff: AgentHandoff;
  agents: Agent[];
  onApprove?: (handoffId: string) => void;
  onReject?: (handoffId: string) => void;
}> = ({ handoff, agents, onApprove, onReject }) => {
  const fromAgent = agents.find((a) => a.id === handoff.fromAgent);
  const toAgent = agents.find((a) => a.id === handoff.toAgent);

  /** Get the status configuration for a handoff */
  const statusConfig:
    | (typeof HANDOFF_STATUS_COLORS)[keyof typeof HANDOFF_STATUS_COLORS]
    | typeof DEFAULT_HANDOFF_STATUS_COLOR =
    HANDOFF_STATUS_COLORS[handoff.status] ?? DEFAULT_HANDOFF_STATUS_COLOR;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "p-4 rounded-lg border transition-all duration-200",
        statusConfig.bg,
        statusConfig.border
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <ArrowRightLeftIcon className={cn("h-4 w-4", statusConfig.text)} />
          <Badge variant="outline" className={statusConfig.text}>
            {handoff.status}
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground">
          {handoff.timestamp.toLocaleTimeString()}
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3">
        <div className="text-center">
          <div className="text-xs text-muted-foreground mb-1">From</div>
          <div className="text-sm font-medium">{fromAgent?.name}</div>
        </div>
        <ArrowRightLeftIcon className="h-4 w-4 text-muted-foreground" />
        <div className="text-center">
          <div className="text-xs text-muted-foreground mb-1">To</div>
          <div className="text-sm font-medium">{toAgent?.name}</div>
        </div>
      </div>

      <div className="space-y-2">
        <div>
          <div className="text-xs text-muted-foreground mb-1">Task</div>
          <div className="text-sm">{handoff.task}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-1">Reason</div>
          <div className="text-sm">{handoff.reason}</div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Confidence:</span>
          <span className="text-xs font-medium">
            {Math.round(handoff.confidence * 100)}%
          </span>
          <Progress value={handoff.confidence * 100} className="w-16 h-1.5" />
        </div>

        {handoff.status === "pending" && (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => onReject?.(handoff.id)}
              className="h-7 px-2 text-xs"
            >
              Reject
            </Button>
            <Button
              size="sm"
              onClick={() => onApprove?.(handoff.id)}
              className="h-7 px-2 text-xs"
            >
              Approve
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  );
};

/** Component for the AgentCollaborationHub */
export const AgentCollaborationHub: React.FC<AgentCollaborationHubProps> = ({
  agents: initialAgents = MockAgents,
  handoffs: initialHandoffs = MockHandoffs,
  onAgentSelect,
  onHandoffApprove,
  onHandoffReject,
  className,
}) => {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // Using React 19's useOptimistic for immediate UI updates
  const [optimisticAgents, updateOptimisticAgents] = useOptimistic(
    initialAgents,
    (_state, newAgents: Agent[]) => newAgents
  );

  const [optimisticHandoffs, updateOptimisticHandoffs] = useOptimistic(
    initialHandoffs,
    (_state, newHandoffs: AgentHandoff[]) => newHandoffs
  );

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      startTransition(() => {
        // Update agent workloads and performance (deterministic - no randomness)
        const updatedAgents = optimisticAgents.map((agent) => ({
          ...agent,
          lastActive: agent.status === "active" ? new Date() : agent.lastActive,
          // Performance metrics remain unchanged (deterministic behavior)
          performance: agent.performance,
          workload: agent.workload,
        }));
        updateOptimisticAgents(updatedAgents);
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [optimisticAgents, updateOptimisticAgents]);

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgent(agentId);
    onAgentSelect?.(agentId);
  };

  const handleHandoffApprove = (handoffId: string) => {
    startTransition(() => {
      const updatedHandoffs = optimisticHandoffs.map((handoff) =>
        handoff.id === handoffId
          ? { ...handoff, status: "completed" as const }
          : handoff
      );
      updateOptimisticHandoffs(updatedHandoffs);
    });
    onHandoffApprove?.(handoffId);
  };

  const handleHandoffReject = (handoffId: string) => {
    startTransition(() => {
      const updatedHandoffs = optimisticHandoffs.map((handoff) =>
        handoff.id === handoffId ? { ...handoff, status: "failed" as const } : handoff
      );
      updateOptimisticHandoffs(updatedHandoffs);
    });
    onHandoffReject?.(handoffId);
  };

  const activeAgents = optimisticAgents.filter((a) => a.status === "active").length;
  // const averageWorkload = // Future implementation
  //   optimisticAgents.reduce((sum, a) => sum + a.workload, 0) / optimisticAgents.length;
  const pendingHandoffs = optimisticHandoffs.filter(
    (h) => h.status === "pending"
  ).length;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <UsersIcon className="h-6 w-6" />
            Agent Collaboration Hub
          </h2>
          <p className="text-gray-600 mt-1">
            Monitor multi-agent coordination and handoffs
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="flex items-center gap-1">
            <ActivityIcon className="h-3 w-3" />
            {activeAgents} Active
          </Badge>
          <Badge variant="outline" className="flex items-center gap-1">
            <ClockIcon className="h-3 w-3" />
            {pendingHandoffs} Pending
          </Badge>
        </div>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {CollaborationMetrics.map((metric) => (
          <Card key={metric.metric}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm text-muted-foreground">{metric.metric}</div>
                <div className="flex items-center gap-1">
                  {metric.trend === "up" && (
                    <TrendingUpIcon className={cn("h-3 w-3", TREND_COLORS.up)} />
                  )}
                  {metric.trend === "down" && (
                    <TrendingDownIcon className={cn("h-3 w-3", TREND_COLORS.down)} />
                  )}
                  {metric.trend === "stable" && (
                    <ActivityIcon className={cn("h-3 w-3", TREND_COLORS.stable)} />
                  )}
                </div>
              </div>
              <div className="text-2xl font-bold mb-1">{metric.value}%</div>
              <div className="text-xs text-muted-foreground">{metric.description}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent Grid */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BrainIcon className="h-5 w-5" />
              Active Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <AnimatePresence>
                {optimisticAgents.map((agent) => (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    onSelect={handleAgentSelect}
                    isSelected={selectedAgent === agent.id}
                  />
                ))}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>

        {/* Handoffs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <WorkflowIcon className="h-5 w-5" />
              Agent Handoffs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <AnimatePresence>
                {optimisticHandoffs.map((handoff) => (
                  <HandoffCard
                    key={handoff.id}
                    handoff={handoff}
                    agents={optimisticAgents}
                    onApprove={handleHandoffApprove}
                    onReject={handleHandoffReject}
                  />
                ))}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Collaboration Flow Visualization */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <NetworkIcon className="h-5 w-5" />
            Collaboration Flow
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center text-muted-foreground">
              <GitBranchIcon className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>Collaboration flow visualization coming soon</p>
              <p className="text-sm">Real-time agent workflow diagram</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AgentCollaborationHub;
