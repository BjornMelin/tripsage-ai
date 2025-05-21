"use client";

import { useParams } from "next/navigation";
import { ChatInterface } from "@/components/chat/chat-interface";

export default function ChatSessionPage() {
  const params = useParams();
  const sessionId = params.id as string;

  return (
    <ChatInterface
      sessionId={sessionId}
      placeholder="Continue your conversation..."
      className="h-full"
    />
  );
}