"use client";

import { ChatLayout } from "@/components/layouts/chat-layout";
import { useChatStore } from "@/stores/chat-store";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { createSession } = useChatStore();

  const handleNewChat = () => {
    createSession();
    // TODO: Navigate to new chat session
    // For now, just trigger the store action
  };

  return (
    <ChatLayout onNewChat={handleNewChat} showAgentPanel={true}>
      {children}
    </ChatLayout>
  );
}
