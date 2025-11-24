/**
 * @fileoverview Conversation memory API route.
 *
 * Adds conversation memory using memory tools.
 * Server-only route that uses addConversationMemory tool.
 */

import "server-only";

import { addConversationMemory } from "@ai/tools";
import {
  type MemoryAddConversationRequest,
  memoryAddConversationSchema,
} from "@schemas/memory";
import { type NextRequest, NextResponse } from "next/server";
import { createUnifiedErrorResponse } from "@/lib/api/error-response";
import { withApiGuards } from "@/lib/api/factory";

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
})(async (_req: NextRequest, { user }, validated: MemoryAddConversationRequest) => {
  if (!user?.id) {
    return createUnifiedErrorResponse({
      error: "unauthorized",
      reason: "Authentication required",
      status: 401,
    });
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
    return createUnifiedErrorResponse({
      err: error,
      error: "internal",
      reason: "Failed to add conversation memory",
      status: 500,
    });
  }
});
