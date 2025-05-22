"use client";

import { ChatInterface } from "@/components/chat/chat-interface";

export default function ChatPage() {
  return (
    <ChatInterface
      placeholder="Ask me about flights, hotels, destinations, or any travel questions..."
      className="h-full"
    />
  );
}
