import "server-only";

/**
 * @fileoverview Chat page shell that hosts the client chat experience with an error boundary.
 */

import type { ReactElement } from "react";
import { ErrorBoundary } from "@/components/error/error-boundary";
import { ChatClient } from "./chat-client";

export const dynamic = "force-dynamic";

export default function ChatPage(): ReactElement {
  return (
    <ErrorBoundary>
      <ChatClient />
    </ErrorBoundary>
  );
}
