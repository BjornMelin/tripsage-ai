"use client";

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
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  ArrowRightLeft,
  Brain,
  CheckCircle2,
  Clock,
  GitBranch,
  Network,
  Timer,
  TrendingUp,
  Users,
  Workflow,
} from "lucide-react";
import type React from "react";
import { startTransition, useEffect, useOptimistic, useState } from "react";

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

interface CollaborationMetric {
  metric: string;
  value: number;
  trend: "up" | "down" | "stable";
  description: string;
}

interface AgentCollaborationHubProps {
  agents: Agent[];
  handoffs: AgentHandoff[];
  onAgentSelect?: (agentId: string) => void;
  onHandoffApprove?: (handoffId: string) => void;
  onHandoffReject?: (handoffId: string) => void;
  className?: string;
}

const mockAgents: Agent[] = [
  {
    id: "agent-1",
    name: "Research Agent",
    avatar: "/agents/research.jpg",
    status: "active",
    specialization: "Data Analysis",
    currentTask: "Market trend analysis",
    performance: { accuracy: 94, speed: 87, efficiency: 91 },
    workload: 75,
    lastActive: new Date(),
  },
  {
    id: "agent-2",
    name: "Planning Agent",
    avatar: "/agents/planning.jpg",
    status: "busy",
    specialization: "Trip Planning",
    currentTask: "Itinerary optimization",
    performance: { accuracy: 89, speed: 92, efficiency: 88 },
    workload: 90,
    lastActive: new Date(Date.now() - 300000),
  },
  {
    id: "agent-3",
    name: "Booking Agent",
    avatar: "/agents/booking.jpg",
    status: "idle",
    specialization: "Reservations",
    performance: { accuracy: 96, speed: 85, efficiency: 93 },
    workload: 25,
    lastActive: new Date(Date.now() - 600000),
  },
  {
    id: "agent-4",
    name: "Support Agent",
    avatar: "/agents/support.jpg",
    status: "active",
    specialization: "Customer Service",
    currentTask: "Query resolution",
    performance: { accuracy: 92, speed: 88, efficiency: 90 },
    workload: 60,
    lastActive: new Date(Date.now() - 120000),
  },
];

const mockHandoffs: AgentHandoff[] = [
  {
    id: "handoff-1",
    fromAgent: "agent-1",
    toAgent: "agent-2",
    task: "Create itinerary from research data",
    reason: "Research completed, planning phase needed",
    timestamp: new Date(),
    status: "pending",
    confidence: 0.89,
  },
  {
    id: "handoff-2",
    fromAgent: "agent-2",
    toAgent: "agent-3",
    task: "Book selected accommodations",
    reason: "Itinerary approved, booking required",
    timestamp: new Date(Date.now() - 180000),
    status: "completed",
    confidence: 0.92,
  },
];

const collaborationMetrics: CollaborationMetric[] = [
  {
    metric: "Handoff Success Rate",
    value: 94,
    trend: "up",
    description: "Percentage of successful agent handoffs",
  },
  {
    metric: "Task Completion Time",
    value: 87,
    trend: "up",
    description: "Average time to complete collaborative tasks",
  },
  {
    metric: "Agent Utilization",
    value: 73,
    trend: "stable",
    description: "Overall agent workload distribution",
  },
  {
    metric: "Coordination Efficiency",
    value: 91,
    trend: "up",
    description: "How well agents work together",
  },
];

const getStatusColor = (status: Agent["status"]) => {
  switch (status) {
    case "active":
      return "bg-green-500";
    case "busy":
      return "bg-yellow-500";
    case "idle":
      return "bg-blue-500";
    case "offline":
      return "bg-gray-500";
    default:
      return "bg-gray-500";
  }
};

const getStatusIcon = (status: Agent["status"]) => {
  switch (status) {
    case "active":
      return <CheckCircle2 className="h-3 w-3" />;
    case "busy":
      return <Clock className="h-3 w-3" />;
    case "idle":
      return <Timer className="h-3 w-3" />;
    case "offline":
      return <AlertTriangle className="h-3 w-3" />;
    default:
      return <Activity className="h-3 w-3" />;
  }
};

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
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
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
          <div
            className={cn(
              "absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-white flex items-center justify-center",
              getStatusColor(agent.status)
            )}
          >
            <div className="text-white">{getStatusIcon(agent.status)}</div>
          </div>
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

const HandoffCard: React.FC<{
  handoff: AgentHandoff;
  agents: Agent[];
  onApprove?: (handoffId: string) => void;
  onReject?: (handoffId: string) => void;
}> = ({ handoff, agents, onApprove, onReject }) => {
  const fromAgent = agents.find((a) => a.id === handoff.fromAgent);
  const toAgent = agents.find((a) => a.id === handoff.toAgent);

  const getStatusConfig = () => {
    switch (handoff.status) {
      case "pending":
        return {
          color: "text-yellow-600",
          bg: "bg-yellow-50",
          border: "border-yellow-200",
        };
      case "completed":
        return {
          color: "text-green-600",
          bg: "bg-green-50",
          border: "border-green-200",
        };
      case "failed":
        return { color: "text-red-600", bg: "bg-red-50", border: "border-red-200" };
      default:
        return { color: "text-gray-600", bg: "bg-gray-50", border: "border-gray-200" };
    }
  };

  const statusConfig = getStatusConfig();

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
          <ArrowRightLeft className={cn("h-4 w-4", statusConfig.color)} />
          <Badge variant="outline" className={statusConfig.color}>
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
        <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
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

export const AgentCollaborationHub: React.FC<AgentCollaborationHubProps> = ({
  agents: initialAgents = mockAgents,
  handoffs: initialHandoffs = mockHandoffs,
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
        // Update agent workloads and performance
        const updatedAgents = optimisticAgents.map((agent) => ({
          ...agent,
          workload: Math.max(
            0,
            Math.min(100, agent.workload + (Math.random() - 0.5) * 10)
          ),
          performance: {
            ...agent.performance,
            accuracy: Math.max(
              0,
              Math.min(100, agent.performance.accuracy + (Math.random() - 0.5) * 2)
            ),
            speed: Math.max(
              0,
              Math.min(100, agent.performance.speed + (Math.random() - 0.5) * 3)
            ),
            efficiency: Math.max(
              0,
              Math.min(100, agent.performance.efficiency + (Math.random() - 0.5) * 2)
            ),
          },
          lastActive: agent.status === "active" ? new Date() : agent.lastActive,
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
  const _averageWorkload =
    optimisticAgents.reduce((sum, a) => sum + a.workload, 0) / optimisticAgents.length;
  const pendingHandoffs = optimisticHandoffs.filter(
    (h) => h.status === "pending"
  ).length;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-6 w-6" />
            Agent Collaboration Hub
          </h2>
          <p className="text-gray-600 mt-1">
            Monitor multi-agent coordination and handoffs
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="flex items-center gap-1">
            <Activity className="h-3 w-3" />
            {activeAgents} Active
          </Badge>
          <Badge variant="outline" className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {pendingHandoffs} Pending
          </Badge>
        </div>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {collaborationMetrics.map((metric, index) => (
          <Card key={index}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm text-muted-foreground">{metric.metric}</div>
                <div className="flex items-center gap-1">
                  {metric.trend === "up" && (
                    <TrendingUp className="h-3 w-3 text-green-500" />
                  )}
                  {metric.trend === "down" && (
                    <TrendingUp className="h-3 w-3 text-red-500 rotate-180" />
                  )}
                  {metric.trend === "stable" && (
                    <Activity className="h-3 w-3 text-blue-500" />
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
              <Brain className="h-5 w-5" />
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
              <Workflow className="h-5 w-5" />
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
            <Network className="h-5 w-5" />
            Collaboration Flow
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center text-muted-foreground">
              <GitBranch className="h-12 w-12 mx-auto mb-2 opacity-50" />
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
