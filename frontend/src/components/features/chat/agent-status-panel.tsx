"use client";

import React from "react";
import { useChatStore } from "@/stores/chat-store";
import { cn } from "@/lib/utils";
import {
  Bot,
  Activity,
  Loader2,
  BarChart,
  FileSearch,
  Map as MapIcon,
  Plane,
  Circle,
  AlertTriangle,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import type { AgentStatus } from "@/stores/chat-store";

interface AgentStatusPanelProps {
  sessionId?: string;
  className?: string;
  showHeader?: boolean;
}

export function AgentStatusPanel({
  sessionId,
  className,
  showHeader = true,
}: AgentStatusPanelProps) {
  // Get agent status for the specified session from store
  const session = useChatStore((state) =>
    sessionId ? state.sessions.find((s) => s.id === sessionId) : null
  );

  const agentStatus = session?.agentStatus;

  // If no status or not active, don't render
  if (!agentStatus || (!agentStatus.isActive && !agentStatus.statusMessage)) {
    return null;
  }

  const { isActive, currentTask, progress, statusMessage } = agentStatus;

  // Determine the appropriate icon based on the current task
  const getTaskIcon = () => {
    if (!currentTask) return <Bot className="h-4 w-4" />;

    const taskLower = currentTask.toLowerCase();

    if (taskLower.includes("search") || taskLower.includes("find")) {
      return <FileSearch className="h-4 w-4" />;
    }
    if (taskLower.includes("map") || taskLower.includes("location")) {
      return <MapIcon className="h-4 w-4" />;
    }
    if (taskLower.includes("flight") || taskLower.includes("travel")) {
      return <Plane className="h-4 w-4" />;
    }
    if (taskLower.includes("analyze") || taskLower.includes("process")) {
      return <BarChart className="h-4 w-4" />;
    }
    return <Activity className="h-4 w-4" />;
  };

  // Get status color and icon based on activity and message
  const getStatusIndicator = () => {
    if (!isActive) {
      return {
        color: "text-green-500",
        bgColor: "bg-green-500/20",
        icon: <Circle className="h-3 w-3 fill-current" />,
        label: "Idle",
      };
    }

    // Check for error in status message
    const hasError =
      statusMessage?.toLowerCase().includes("error") ||
      statusMessage?.toLowerCase().includes("failed");

    if (hasError) {
      return {
        color: "text-destructive",
        bgColor: "bg-destructive/20",
        icon: <AlertTriangle className="h-3 w-3" />,
        label: "Error",
      };
    }

    // Active status
    return {
      color: "text-blue-500",
      bgColor: "bg-blue-500/20",
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      label: "Active",
    };
  };

  const statusIndicator = getStatusIndicator();

  return (
    <div
      className={cn(
        "bg-background/80 p-3 border rounded-lg shadow-sm",
        className
      )}
    >
      {showHeader && (
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            <span className="font-medium">Agent Status</span>
          </div>

          <div
            className={cn(
              "flex items-center gap-2 text-xs px-2 py-1 rounded-full",
              statusIndicator.color,
              statusIndicator.bgColor
            )}
          >
            {statusIndicator.icon}
            <span>{statusIndicator.label}</span>
          </div>
        </div>
      )}

      {currentTask && (
        <div className="mb-2">
          <div className="flex items-center gap-2 mb-1">
            {getTaskIcon()}
            <span className="text-sm font-medium">{currentTask}</span>
          </div>

          <Progress value={progress || 0} className="h-1" />
        </div>
      )}

      {statusMessage && (
        <div className="text-xs text-muted-foreground mt-2">
          {statusMessage}
        </div>
      )}
    </div>
  );
}
