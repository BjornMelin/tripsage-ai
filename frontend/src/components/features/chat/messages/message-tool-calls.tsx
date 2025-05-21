'use client';

import React, { useState } from 'react';
import { ToolCall, ToolResult } from '@/types/chat';
import { cn } from '@/lib/utils';
import { AlertCircle, Check, ChevronDown, ChevronUp, Loader2, TerminalSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useChatStore } from '@/stores/chat-store';

interface MessageToolCallsProps {
  toolCalls: ToolCall[];
  toolResults?: ToolResult[];
}

export default function MessageToolCalls({ 
  toolCalls, 
  toolResults 
}: MessageToolCallsProps) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="space-y-2 my-1">
      {toolCalls.map((toolCall) => (
        <ToolCallItem 
          key={toolCall.id} 
          toolCall={toolCall}
          result={toolResults?.find(result => result.callId === toolCall.id)?.result}
        />
      ))}
    </div>
  );
}

interface ToolCallItemProps {
  toolCall: ToolCall;
  result?: any;
}

function ToolCallItem({ toolCall, result }: ToolCallItemProps) {
  const [expanded, setExpanded] = useState(false);
  const { addToolResult } = useChatStore();
  
  const isPartialCall = toolCall.state === 'partial-call';
  const isFullCall = toolCall.state === 'call';
  const hasResult = toolCall.state === 'result' || result;
  
  // Format JSON for display
  const formatJSON = (obj: any) => {
    try {
      return typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2);
    } catch (e) {
      return String(obj);
    }
  };
  
  const handleToolConfirm = () => {
    if (!toolCall.sessionId) return;
    
    // In a real implementation, this would perform the actual tool action
    // For now, we'll just simulate a result
    addToolResult({
      sessionId: toolCall.sessionId,
      messageId: toolCall.messageId,
      callId: toolCall.id,
      result: { success: true, data: 'Tool action completed successfully' }
    });
  };
  
  return (
    <div className="border rounded-md overflow-hidden">
      <div 
        className="bg-secondary/50 p-2 flex items-center justify-between cursor-pointer hover:bg-secondary/70"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <TerminalSquare className="h-4 w-4" />
          <span className="font-medium text-sm">{toolCall.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {isPartialCall && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
          {isFullCall && (
            <Button 
              variant="ghost" 
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                handleToolConfirm();
              }}
            >
              Confirm
            </Button>
          )}
          {hasResult && <Check className="h-4 w-4 text-green-500" />}
          
          {expanded ? 
            <ChevronUp className="h-4 w-4 text-muted-foreground" /> : 
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          }
        </div>
      </div>
      
      {expanded && (
        <div className="p-2 text-sm">
          <div className="font-mono text-xs bg-background rounded p-1 overflow-x-auto">
            <pre className="whitespace-pre-wrap">{formatJSON(toolCall.arguments)}</pre>
          </div>
          
          {hasResult && (
            <div className="mt-2 border-t pt-2">
              <div className="text-xs text-muted-foreground mb-1">Result:</div>
              <div className="font-mono text-xs bg-background rounded p-1 overflow-x-auto">
                <pre className="whitespace-pre-wrap">{formatJSON(result)}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}