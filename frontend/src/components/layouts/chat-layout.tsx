'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw, Settings, Terminal, Trash2 } from 'lucide-react';

interface ChatLayoutProps {
  children: React.ReactNode;
}

export default function ChatLayout({ children }: ChatLayoutProps) {
  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* Sidebar */}
      <div className="w-[300px] border-r p-4 flex flex-col bg-background">
        <div className="mb-4">
          <Button className="w-full" variant="default">
            <Plus className="mr-2 h-4 w-4" />
            <span>New Chat</span>
          </Button>
        </div>

        <div className="flex-1 overflow-auto">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground mb-2">Recent chats</p>
            {/* Chat sessions list will be populated here */}
            <ChatSessionItem
              title="Trip to Japan in 2025"
              timestamp="2 hours ago"
              active
            />
            <ChatSessionItem
              title="Best places to visit in Europe"
              timestamp="2 days ago"
            />
            <ChatSessionItem
              title="Budget planning for summer vacation"
              timestamp="1 week ago"
            />
          </div>
        </div>

        <div className="mt-auto pt-4 border-t">
          <Button variant="ghost" size="sm" className="w-full justify-start mb-2">
            <Settings className="mr-2 h-4 w-4" />
            <span>Settings</span>
          </Button>
          <Button variant="ghost" size="sm" className="w-full justify-start">
            <Terminal className="mr-2 h-4 w-4" />
            <span>Agent Status</span>
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        <div className="border-b p-4 flex items-center justify-between bg-background">
          <h1 className="text-lg font-semibold">Current Chat</h1>
          <div className="flex space-x-2">
            <Button variant="ghost" size="icon">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon">
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        <div className="flex-1 overflow-auto p-4">
          {children}
        </div>
      </div>
      
      {/* Agent status sidebar can be added here */}
    </div>
  );
}

interface ChatSessionItemProps {
  title: string;
  timestamp: string;
  active?: boolean;
}

function ChatSessionItem({ title, timestamp, active }: ChatSessionItemProps) {
  return (
    <div
      className={cn(
        "p-3 rounded-md cursor-pointer hover:bg-accent",
        active && "bg-accent"
      )}
    >
      <div className="flex flex-col">
        <span className="text-sm font-medium">{title}</span>
        <span className="text-xs text-muted-foreground">{timestamp}</span>
      </div>
    </div>
  );
}