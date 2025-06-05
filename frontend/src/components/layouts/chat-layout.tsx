"use client";

import { cn } from "@/lib/utils";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import { useChatStore } from "@/stores/chat-store";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo } from "react";

interface ChatSidebarProps extends React.HTMLAttributes<HTMLElement> {
  onNewChat?: () => void;
}

// Sample chat sessions for placeholder functionality
const SAMPLE_SESSIONS = [
  {
    id: "1",
    title: "Flight Search Help",
    lastMessage: "Find me flights to Paris",
    updatedAt: "2025-05-21T10:00:00Z",
  },
  {
    id: "2",
    title: "Budget Planning",
    lastMessage: "How can I save money on travel?",
    updatedAt: "2025-05-21T09:30:00Z",
  },
  {
    id: "3",
    title: "Hotel Recommendations",
    lastMessage: "Best hotels in Tokyo",
    updatedAt: "2025-05-21T08:45:00Z",
  },
];

function ChatSidebar({ className, onNewChat, ...props }: ChatSidebarProps) {
  const pathname = usePathname();
  const currentChatId = pathname.split("/").pop();

  return (
    <nav
      className={cn("flex flex-col h-full bg-muted/30 border-r", className)}
      {...props}
    >
      {/* New Chat Button */}
      <div className="p-4 border-b">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Chat
        </button>
      </div>

      {/* Chat Sessions List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Recent Chats
          </h3>
          <div className="space-y-1">
            {SAMPLE_SESSIONS.map((session) => (
              <Link
                key={session.id}
                href={`/dashboard/chat/${session.id}`}
                className={cn(
                  "flex flex-col p-3 rounded-md text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
                  currentChatId === session.id
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground"
                )}
              >
                <div className="font-medium truncate mb-1">{session.title}</div>
                <div className="text-xs opacity-70 truncate">{session.lastMessage}</div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Settings */}
      <div className="p-4 border-t">
        <Link
          href="/dashboard/settings"
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          Chat Settings
        </Link>
      </div>
    </nav>
  );
}

interface AgentStatusPanelProps extends React.HTMLAttributes<HTMLElement> {}

function AgentStatusPanel({ className, ...props }: AgentStatusPanelProps) {
  const { agents, isLoading } = useAgentStatusStore();

  // Get active agents
  const activeAgents = useMemo(
    () => agents.filter((agent) => agent.status === "active"),
    [agents]
  );

  return (
    <div
      className={cn("w-80 bg-muted/30 border-l p-4 overflow-y-auto", className)}
      {...props}
    >
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">Agent Status</h3>
          <div
            className={cn(
              "w-2 h-2 rounded-full",
              isLoading
                ? "bg-yellow-500"
                : activeAgents.length > 0
                  ? "bg-green-500"
                  : "bg-gray-400"
            )}
          />
        </div>

        {/* Active Agents */}
        {activeAgents.length > 0 ? (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Active ({activeAgents.length})
            </h4>
            {activeAgents.map((agent) => (
              <div key={agent.id} className="p-3 bg-background rounded-lg border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{agent.name}</span>
                  <span className="text-xs text-green-600 bg-green-100 px-2 py-1 rounded-full">
                    {agent.status}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {agent.currentTask || "Waiting for tasks..."}
                </div>
                {agent.progress && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-primary h-1.5 rounded-full transition-all"
                        style={{ width: `${agent.progress}%` }}
                      />
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {agent.progress}% complete
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center mx-auto mb-3">
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
            <p className="text-sm">No active agents</p>
            <p className="text-xs">Start a conversation to see agent activity</p>
          </div>
        )}

        {/* Recent Activity */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Recent Activity
          </h4>
          <div className="space-y-2">
            <div className="text-xs p-2 bg-background rounded border">
              <span className="text-muted-foreground">Flight Agent:</span> Found 12
              results for Paris
            </div>
            <div className="text-xs p-2 bg-background rounded border">
              <span className="text-muted-foreground">Budget Agent:</span> Calculated
              trip estimate
            </div>
            <div className="text-xs p-2 bg-background rounded border">
              <span className="text-muted-foreground">Weather Agent:</span> Retrieved
              forecast data
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ChatLayoutProps {
  children: React.ReactNode;
  showAgentPanel?: boolean;
  onNewChat?: () => void;
  sidebarCollapsed?: boolean;
}

export function ChatLayout({
  children,
  showAgentPanel = true,
  onNewChat,
  sidebarCollapsed = false,
}: ChatLayoutProps) {
  return (
    <div className="flex h-full max-h-screen overflow-hidden">
      {/* Chat Sidebar */}
      <div
        className={cn(
          "flex-shrink-0 transition-all duration-300",
          sidebarCollapsed ? "w-0 overflow-hidden" : "w-80"
        )}
      >
        <ChatSidebar onNewChat={onNewChat} />
      </div>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 relative">{children}</main>

      {/* Agent Status Panel */}
      {showAgentPanel && (
        <div className="flex-shrink-0 hidden lg:block">
          <AgentStatusPanel />
        </div>
      )}
    </div>
  );
}

// Export individual components for flexibility
export { ChatSidebar, AgentStatusPanel };
