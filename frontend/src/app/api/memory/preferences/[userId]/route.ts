/**
 * @fileoverview Memory preferences API route.
 *
 * Updates user preferences using memory tools.
 * Server-only route that uses addConversationMemory tool.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, validateSchema } from "@/lib/next/route-helpers";
import { addConversationMemory } from "@/lib/tools/memory";

const updatePreferencesSchema = z.object({
  merge_strategy: z.enum(["merge", "replace"]).default("merge"),
  preferences: z.record(z.string(), z.unknown()),
});

/**
 * POST /api/memory/preferences/[userId]
 *
 * Update user preferences using memory tools.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:preferences",
  telemetry: "memory.preferences",
})(async (req: NextRequest, { user }) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(updatePreferencesSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const { preferences } = validation.data;

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
