/**
 * @fileoverview Chat interface page component for AI travel assistant.
 *
 * Provides the main chat interface for interacting with the TripSage AI travel
 * assistant. Features real-time messaging, agent collaboration, and integrated
 * chat functionality with WebSocket support for live updates and typing
 * indicators.
 */

"use client";

import { ChatContainer } from "@/components/chat/chat-container";

// Mock current user - in a real app, this would come from auth context
const currentUser = {
  id: "user-1",
  name: "User",
  avatar: undefined,
};

/**
 * Chat page component for AI travel assistant interface.
 *
 * Renders the main chat interface for interacting with the TripSage AI travel
 * assistant. Provides a full-height chat container with responsive design and
 * integrated agent collaboration features.
 *
 * Features:
 * - Full-height responsive chat interface
 * - AI travel assistant integration
 * - Real-time messaging capabilities
 * - Agent collaboration and tool calling
 * - Header display with assistant branding
 *
 * @returns {JSX.Element} The rendered chat page with AI assistant interface.
 */
export default function ChatPage() {
  return (
    <div className="h-full p-6">
      <div className="h-full max-w-4xl mx-auto">
        <ChatContainer
          currentUser={currentUser}
          title="AI Travel Assistant"
          showHeader
          className="h-full shadow-lg"
        />
      </div>
    </div>
  );
}
