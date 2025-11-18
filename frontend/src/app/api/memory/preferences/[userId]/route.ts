/**
 * @fileoverview Memory preferences API route.
 *
 * Updates user preferences using memory tools.
 * Server-only route that uses addConversationMemory tool.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  type MemoryUpdatePreferencesRequest,
  memoryUpdatePreferencesSchema,
} from "@/lib/schemas/memory";
import { addConversationMemory } from "@/lib/tools/memory";

/**
 * POST /api/memory/preferences/[userId]
 *
 * Update user preferences using memory tools.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:preferences",
  schema: memoryUpdatePreferencesSchema,
  telemetry: "memory.preferences",
})(async (req: NextRequest, { user }, validated: MemoryUpdatePreferencesRequest) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { preferences } = validated;

  try {
    if (!addConversationMemory.execute) {
      throw new Error("tool_execute_not_available");
    }

    // Store preferences as memory entries
    const preferenceEntries = Object.entries(preferences).map(([key, value]) => ({
      category: "user_preference" as const,
      content: `${key}: ${JSON.stringify(value)}`,
    }));

    const results = await Promise.all(
      preferenceEntries.map(async (entry, index) => {
        if (!addConversationMemory.execute) {
          throw new Error("tool_execute_not_available");
        }
        // AI SDK tools require context parameter (toolCallId, messages)
        const result = await addConversationMemory.execute(
          {
            category: entry.category,
            content: entry.content,
          },
          {
            messages: [],
            toolCallId: `memory-pref-${Date.now()}-${index}`,
          }
        );
        if (
          result &&
          typeof result === "object" &&
          "createdAt" in result &&
          "id" in result
        ) {
          return {
            createdAt: result.createdAt as string,
            id: result.id as string,
          };
        }
        throw new Error("unexpected_tool_result");
      })
    );

    return NextResponse.json({
      preferences: Object.fromEntries(
        Object.entries(preferences).map(([key], index) => [
          key,
          { createdAt: results[index]?.createdAt, id: results[index]?.id },
        ])
      ),
      updated: results.length,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "preferences_update_failed",
        message:
          error instanceof Error ? error.message : "Failed to update preferences",
      },
      { status: 500 }
    );
  }
});
