"use client";

import type React from "react";
import { useState, useEffect } from "react";
import type { ToolCall, ToolResult } from "@/types/chat";
import { cn } from "@/lib/utils";
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  TerminalSquare,
  MapPin,
  Plane,
  Building,
  CloudSun,
  Calendar,
  Search,
  X,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useChatStore } from "@/stores/chat-store";

interface MessageToolCallsProps {
  toolCalls: ToolCall[];
  toolResults?: ToolResult[];
  onRetryToolCall?: (toolCallId: string) => void;
  onCancelToolCall?: (toolCallId: string) => void;
}

// Icon mapping for different tool types
const getToolIcon = (toolName: string) => {
  const iconMap: Record<string, React.ComponentType<any>> = {
    // Travel tools
    search_flights: Plane,
    search_accommodations: Building,
    get_weather: CloudSun,
    search_places: MapPin,
    get_directions: MapPin,

    // General tools
    web_search: Search,
    get_calendar: Calendar,
    time_tools: Clock,

    // Default
    default: TerminalSquare,
  };

  return iconMap[toolName] || iconMap.default;
};

// Get tool category for styling
const getToolCategory = (toolName: string): string => {
  if (toolName.includes("flight") || toolName.includes("Plane"))
    return "flight";
  if (toolName.includes("accommodation") || toolName.includes("hotel"))
    return "accommodation";
  if (toolName.includes("weather")) return "weather";
  if (toolName.includes("map") || toolName.includes("place")) return "location";
  if (toolName.includes("calendar") || toolName.includes("time")) return "time";
  return "general";
};

// Get category color
const getCategoryColor = (category: string): string => {
  const colorMap: Record<string, string> = {
    flight: "bg-blue-100 text-blue-800 border-blue-200",
    accommodation: "bg-green-100 text-green-800 border-green-200",
    weather: "bg-orange-100 text-orange-800 border-orange-200",
    location: "bg-purple-100 text-purple-800 border-purple-200",
    time: "bg-indigo-100 text-indigo-800 border-indigo-200",
    general: "bg-gray-100 text-gray-800 border-gray-200",
  };
  return colorMap[category] || colorMap.general;
};

export default function MessageToolCalls({
  toolCalls,
  toolResults,
  onRetryToolCall,
  onCancelToolCall,
}: MessageToolCallsProps) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="space-y-2 my-2">
      <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
        <TerminalSquare className="h-3 w-3" />
        Tool Execution ({toolCalls.length})
      </div>
      {toolCalls.map((toolCall) => (
        <ToolCallItem
          key={toolCall.id}
          toolCall={toolCall}
          result={
            toolResults?.find((result) => result.callId === toolCall.id)?.result
          }
          onRetry={onRetryToolCall}
          onCancel={onCancelToolCall}
        />
      ))}
    </div>
  );
}

interface ToolCallItemProps {
  toolCall: ToolCall;
  result?: any;
  onRetry?: (toolCallId: string) => void;
  onCancel?: (toolCallId: string) => void;
}

function ToolCallItem({
  toolCall,
  result,
  onRetry,
  onCancel,
}: ToolCallItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [localStatus, setLocalStatus] = useState(toolCall.status || "pending");
  const { addToolResult } = useChatStore();

  // Update local status when toolCall.status changes
  useEffect(() => {
    if (toolCall.status) {
      setLocalStatus(toolCall.status);
    }
  }, [toolCall.status]);

  const ToolIcon = getToolIcon(toolCall.name);
  const category = getToolCategory(toolCall.name);
  const categoryColor = getCategoryColor(category);

  const isPending = localStatus === "pending";
  const isExecuting = localStatus === "executing";
  const isCompleted = localStatus === "completed";
  const hasError = localStatus === "error" || toolCall.error;

  // Format JSON for display
  const formatJSON = (obj: any) => {
    try {
      return typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
    } catch (e) {
      return String(obj);
    }
  };

  // Format tool result for better display
  const formatToolResult = (result: any) => {
    if (!result) return null;

    if (typeof result === "object" && result.status === "success") {
      return result.result || result.data || result;
    }

    if (typeof result === "object" && result.status === "error") {
      return { error: result.error || result.message || "Unknown error" };
    }

    return result;
  };

  const handleToolConfirm = () => {
    if (!toolCall.sessionId) return;

    setLocalStatus("executing");

    // Simulate execution delay
    setTimeout(() => {
      setLocalStatus("completed");
      addToolResult({
        sessionId: toolCall.sessionId!,
        messageId: toolCall.messageId!,
        callId: toolCall.id,
        result: { success: true, data: "Tool action completed successfully" },
      });
    }, 1500);
  };

  const handleRetry = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onRetry) {
      setLocalStatus("pending");
      onRetry(toolCall.id);
    }
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onCancel) {
      setLocalStatus("cancelled");
      onCancel(toolCall.id);
    }
  };

  // Get status badge
  const getStatusBadge = () => {
    if (isExecuting) {
      return (
        <Badge variant="secondary" className="text-xs flex items-center gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          Executing...
        </Badge>
      );
    }

    if (isCompleted) {
      return (
        <Badge
          variant="secondary"
          className="text-xs bg-green-100 text-green-800 flex items-center gap-1"
        >
          <Check className="h-3 w-3" />
          Completed
        </Badge>
      );
    }

    if (hasError) {
      return (
        <Badge
          variant="destructive"
          className="text-xs flex items-center gap-1"
        >
          <AlertCircle className="h-3 w-3" />
          Error
        </Badge>
      );
    }

    if (isPending) {
      return (
        <Badge variant="outline" className="text-xs flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Pending
        </Badge>
      );
    }

    return null;
  };

  // Execution time display
  const executionTime =
    toolCall.executionTime || (isCompleted && result?.executionTime)
      ? ` (${(toolCall.executionTime || result.executionTime).toFixed(2)}s)`
      : "";

  return (
    <div
      className={cn(
        "border rounded-lg overflow-hidden transition-all duration-200",
        hasError && "border-red-200 bg-red-50/50",
        isCompleted && "border-green-200 bg-green-50/50",
        isExecuting && "border-blue-200 bg-blue-50/50"
      )}
    >
      <div
        className={cn(
          "p-3 flex items-center justify-between cursor-pointer hover:bg-secondary/30 transition-colors",
          "bg-secondary/20"
        )}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={cn("p-1.5 rounded border", categoryColor)}>
            <ToolIcon className="h-4 w-4" />
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{toolCall.name}</span>
              {getStatusBadge()}
            </div>
            {executionTime && (
              <span className="text-xs text-muted-foreground">
                Executed in {executionTime}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Action buttons */}
          {hasError && onRetry && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={handleRetry}
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          )}

          {isExecuting && onCancel && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-red-600 hover:text-red-700"
              onClick={handleCancel}
            >
              <X className="h-3 w-3 mr-1" />
              Cancel
            </Button>
          )}

          {isPending && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                handleToolConfirm();
              }}
            >
              Execute
            </Button>
          )}

          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="p-3 pt-0 text-sm border-t bg-background/50">
          {/* Tool Arguments */}
          {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
            <div className="mb-3">
              <div className="text-xs font-medium text-muted-foreground mb-2">
                Parameters:
              </div>
              <div className="font-mono text-xs bg-background rounded border p-2 overflow-x-auto">
                <pre className="whitespace-pre-wrap">
                  {formatJSON(toolCall.arguments)}
                </pre>
              </div>
            </div>
          )}

          {/* Tool Result */}
          {(result || toolCall.result) && (
            <div className="mb-3">
              <div className="text-xs font-medium text-muted-foreground mb-2">
                Result:
              </div>
              <div className="font-mono text-xs bg-background rounded border p-2 overflow-x-auto">
                <pre className="whitespace-pre-wrap">
                  {formatJSON(formatToolResult(result || toolCall.result))}
                </pre>
              </div>
            </div>
          )}

          {/* Error Display */}
          {toolCall.error && (
            <div className="mb-3">
              <div className="text-xs font-medium text-red-600 mb-2">
                Error:
              </div>
              <div className="text-xs bg-red-50 text-red-800 rounded border border-red-200 p-2">
                {toolCall.error}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span>ID: {toolCall.id}</span>
            {toolCall.executionTime && (
              <span>Execution Time: {toolCall.executionTime.toFixed(2)}s</span>
            )}
            <span>Category: {category}</span>
          </div>
        </div>
      )}
    </div>
  );
}
