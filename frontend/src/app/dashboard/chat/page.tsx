"use client";

import { ChatContainer } from "@/components/chat/chat-container";

// Mock current user - in a real app, this would come from auth context
const currentUser = {
  id: "user-1",
  name: "User",
  avatar: undefined,
};

export default function ChatPage() {
  return (
    <div className="h-full p-6">
      <div className="h-full max-w-4xl mx-auto">
        <ChatContainer
          currentUser={currentUser}
          title="AI Travel Assistant"
          showHeader={true}
          className="h-full shadow-lg"
          websocketUrl={
            process.env.NODE_ENV === "development"
              ? "ws://localhost:8080/ws"
              : "wss://api.tripsage.ai/ws"
          }
        />
      </div>
    </div>
  );
}
