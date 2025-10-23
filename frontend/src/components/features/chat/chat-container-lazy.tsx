"use client";

import dynamic from "next/dynamic";
import type { ComponentProps } from "react";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

// Dynamically import the ChatContainer to reduce initial bundle size
const ChatContainer = dynamic(
  () => import("./chat-container").then((mod) => ({ default: mod.ChatContainer })),
  {
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <LoadingSpinner size="lg" />
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Loading Chat Interface</h3>
            <p className="text-sm text-muted-foreground">
              Setting up your AI-powered chat experience...
            </p>
          </div>
        </div>
      </div>
    ),
    ssr: false, // Chat interface is client-only
  }
);

type ChatContainerProps = ComponentProps<typeof ChatContainer>;

export { ChatContainer };
export type { ChatContainerProps };
