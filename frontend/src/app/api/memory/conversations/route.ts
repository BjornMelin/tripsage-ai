/**
 * @fileoverview Conversation memory API route.
 *
 * Adds conversation memory using memory tools.
 * Server-only route that uses addConversationMemory tool.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  type MemoryAddConversationRequest,
  memoryAddConversationSchema,
} from "@/lib/schemas/memory";
import { addConversationMemory } from "@/lib/tools/memory";

/**
 * POST /api/memory/conversations
 *
 * Add conversation memory using memory tools.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:conversations",
  schema: memoryAddConversationSchema,
  telemetry: "memory.conversations",
})(async (req: NextRequest, { user }, validated: MemoryAddConversationRequest) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { category, content } = validated;

  try {
    if (!addConversationMemory.execute) {
      throw new Error("tool_execute_not_available");
    }
    // AI SDK tools require context parameter (toolCallId, messages)
    const result = await addConversationMemory.execute(
      {
        category,
        content,
      },
      {
        messages: [],
        toolCallId: `memory-${Date.now()}`,
      }
    );

    if (
      result &&
      typeof result === "object" &&
      "createdAt" in result &&
      "id" in result
    ) {
      return NextResponse.json({
        createdAt: result.createdAt as string,
        id: result.id as string,
      });
    }

    throw new Error("unexpected_tool_result");
  } catch (error) {
    return NextResponse.json(
      {
        error: "conversation_memory_add_failed",
        message:
          error instanceof Error ? error.message : "Failed to add conversation memory",
      },
      { status: 500 }
    );
  }
});
