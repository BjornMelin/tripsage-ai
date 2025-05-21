'use client';

import React from 'react';
import { useChatStore } from '@/stores/chat-store';
import { cn } from '@/lib/utils';
import { Bot, Activity, Loader2, BarChart, FileSearch, Map, Plane, Circle, AlertTriangle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { AgentStatus, AgentStatusState } from '@/types/chat';

interface AgentStatusPanelProps {
  sessionId?: string;
  className?: string;
  showHeader?: boolean;
}

export default function AgentStatusPanel({
  sessionId,
  className,
  showHeader = true
}: AgentStatusPanelProps) {
  const { getAgentStatus } = useChatStore();
  
  // Get agent status for the specified session
  const agentStatus = getAgentStatus(sessionId || '');
  
  // If no status or idle with no message, don't render
  if (!agentStatus || (agentStatus.status === 'idle' && !agentStatus.message)) {
    return null;
  }

  const { status, task, progress, message } = agentStatus;
  
  // Determine the appropriate icon based on the current task
  const getTaskIcon = () => {
    if (!task) return <Bot className="h-4 w-4" />;
    
    const taskLower = task.toLowerCase();
    
    if (taskLower.includes('search') || taskLower.includes('find')) {
      return <FileSearch className="h-4 w-4" />;
    } else if (taskLower.includes('map') || taskLower.includes('location')) {
      return <Map className="h-4 w-4" />;
    } else if (taskLower.includes('flight') || taskLower.includes('travel')) {
      return <Plane className="h-4 w-4" />;
    } else if (taskLower.includes('analyze') || taskLower.includes('process')) {
      return <BarChart className="h-4 w-4" />;
    } else {
      return <Activity className="h-4 w-4" />;
    }
  };
  
  // Get status color and icon
  const getStatusIndicator = () => {
    switch (status) {
      case 'thinking':
        return { 
          color: "text-amber-500", 
          bgColor: "bg-amber-500/20",
          icon: <Loader2 className="h-3 w-3 animate-spin" />,
          label: "Thinking"
        };
      case 'processing':
        return { 
          color: "text-blue-500", 
          bgColor: "bg-blue-500/20",
          icon: <Loader2 className="h-3 w-3 animate-spin" />,
          label: "Processing"
        };
      case 'error':
        return { 
          color: "text-destructive", 
          bgColor: "bg-destructive/20",
          icon: <AlertTriangle className="h-3 w-3" />,
          label: "Error"
        };
      case 'idle':
      default:
        return { 
          color: "text-green-500", 
          bgColor: "bg-green-500/20",
          icon: <Circle className="h-3 w-3 fill-current" />,
          label: "Idle"
        };
    }
  };
  
  const statusIndicator = getStatusIndicator();

  return (
    <div className={cn(
      "bg-background/80 p-3 border rounded-lg shadow-sm",
      className
    )}>
      {showHeader && (
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            <span className="font-medium">Agent Status</span>
          </div>
          
          <div className={cn(
            "flex items-center gap-2 text-xs px-2 py-1 rounded-full",
            statusIndicator.color,
            statusIndicator.bgColor
          )}>
            {statusIndicator.icon}
            <span>{statusIndicator.label}</span>
          </div>
        </div>
      )}
      
      {task && (
        <div className="mb-2">
          <div className="flex items-center gap-2 mb-1">
            {getTaskIcon()}
            <span className="text-sm font-medium">{task}</span>
          </div>
          
          <Progress value={progress || 0} className="h-1" />
        </div>
      )}
      
      {message && (
        <div className="text-xs text-muted-foreground mt-2">
          {message}
        </div>
      )}
    </div>
  );
}