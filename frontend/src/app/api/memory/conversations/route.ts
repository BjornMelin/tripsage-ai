/**
 * @fileoverview Conversation memory API route.
 *
 * Adds conversation memory using memory tools.
 * Server-only route that uses addConversationMemory tool.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, validateSchema } from "@/lib/next/route-helpers";
import { addConversationMemory } from "@/lib/tools/memory";

const addConversationMemorySchema = z.object({
  category: z
    .enum([
      "user_preference",
      "trip_history",
      "search_pattern",
      "conversation_context",
      "other",
    ])
    .default("conversation_context"),
  content: z.string().min(1),
  sessionId: z.string().optional(),
});

/**
 * POST /api/memory/conversations
 *
 * Add conversation memory using memory tools.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:conversations",
  telemetry: "memory.conversations",
})(async (req: NextRequest, { user }) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(addConversationMemorySchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const { category, content } = validation.data;

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
