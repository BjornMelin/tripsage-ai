/**
 * @fileoverview Travel planning tools implemented with AI SDK v6.
 * Server-only execution with Redis persistence and optional memory logging.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  combineSearchResultsInputSchema,
  createTravelPlanInputSchema,
  saveTravelPlanInputSchema,
  updateTravelPlanInputSchema,
} from "@ai/tools/schemas/planning";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { z } from "zod";
import { getRedis } from "@/lib/redis";
import { nowIso, secureUuid } from "@/lib/security/random";
import type { Database, Json } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { requireApproval } from "./approvals";
import {
  RATE_CREATE_PER_DAY,
  RATE_UPDATE_PER_MIN,
  TTL_DRAFT_SECONDS,
  TTL_FINAL_SECONDS,
} from "./constants";
import { type Plan, planSchema } from "./planning.schema";

const UUID_V4 = z.uuid();
const planningLogger = createServerLogger("tools.planning");

/** Generate Redis key for travel plan. */
function redisKeyForPlan(planId: string): string {
  return `travel_plan:${planId}`;
}

/** Coerce value to float. */
function coerceFloat(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

/** Read value from object. */
function read<T = unknown>(obj: unknown, key: string): T | undefined {
  if (obj && typeof obj === "object" && key in (obj as Record<string, unknown>)) {
    return (obj as Record<string, unknown>)[key] as T;
  }
  return undefined;
}

/** Record travel plan memory.
 *
 * @param opts Options for recording the travel plan memory.
 * @param opts.userId User ID.
 * @param opts.content Content of the travel plan memory.
 * @param opts.metadata Metadata of the travel plan memory.
 * @returns Promise resolving to void.
 */
async function recordPlanMemory(opts: {
  userId: string;
  content: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  try {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const sessionUserId = auth?.user?.id;
    if (!sessionUserId || sessionUserId !== opts.userId) return;

    const { data: existingSession } = await supabase
      .schema("memories")
      .from("sessions")
      .select("id")
      .eq("user_id", opts.userId)
      .eq("title", "Travel Plan")
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    const sessionId = existingSession?.id ?? secureUuid();

    if (!existingSession) {
      await supabase
        .schema("memories")
        .from("sessions")
        .insert({
          id: sessionId,
          metadata: (opts.metadata ?? null) as Json | null,
          title: "Travel Plan",
          // biome-ignore lint/style/useNamingConvention: Database field name
          user_id: opts.userId,
        });
    }

    await supabase
      .schema("memories")
      .from("turns")
      .insert({
        attachments:
          [] as Database["memories"]["Tables"]["turns"]["Insert"]["attachments"],
        content: { text: opts.content } as Json,
        // biome-ignore lint/style/useNamingConvention: Database field name
        pii_scrubbed: false,
        role: "user",
        // biome-ignore lint/style/useNamingConvention: Database field names
        session_id: sessionId,
        // biome-ignore lint/style/useNamingConvention: Database field name
        tool_calls:
          [] as Database["memories"]["Tables"]["turns"]["Insert"]["tool_calls"],
        // biome-ignore lint/style/useNamingConvention: Database field name
        tool_results:
          [] as Database["memories"]["Tables"]["turns"]["Insert"]["tool_results"],
        // biome-ignore lint/style/useNamingConvention: Database field name
        user_id: opts.userId,
      });
  } catch {
    planningLogger.warn("tools.planning.memory_record_failed", {
      contentLength: opts.content?.length ?? 0,
      userId: opts.userId,
    });
  }
}

/**
 * Convert travel plan to markdown summary.
 *
 * @param plan Travel plan to convert to markdown summary.
 * @returns Markdown summary of the travel plan.
 */
function toMarkdownSummary(plan: Plan): string {
  const title = String(plan.title ?? "Travel Plan");
  const destinations = plan.destinations ?? [];
  const start = plan.startDate ?? "";
  const end = plan.endDate ?? "";
  const travelers = plan.travelers ?? 1;
  const budget = plan.budget ?? undefined;
  const components = plan.components ?? {
    accommodations: [],
    activities: [],
    flights: [],
    notes: [],
    transportation: [],
  };

  let md = `# ${title}\n\n`;
  md += "## Trip Overview\n\n";
  md += `**Destinations**: ${destinations.join(", ")}\n\n`;
  md += `**Dates**: ${start} to ${end}\n\n`;
  md += `**Travelers**: ${travelers}\n\n`;
  if (typeof budget === "number") md += `**Budget**: $${budget}\n\n`;

  const flights = components.flights ?? [];
  if (flights.length) {
    md += "## Flights\n\n";
    flights.forEach((f, i) => {
      md += `### Flight ${i + 1}\n\n`;
      md += `* **From**: ${String(read(f, "origin") ?? "N/A")}\n`;
      md += `* **To**: ${String(read(f, "destination") ?? "N/A")}\n`;
      md += `* **Date**: ${String(read(f, "departureDate") ?? "N/A")}\n`;
      md += `* **Airline**: ${String(read(f, "airline") ?? "N/A")}\n`;
      md += `* **Price**: $${String(read(f, "price") ?? "N/A")}\n\n`;
    });
  }
  return md;
}

/**
 * Tool for creating a new travel plan with destinations, dates, and budget.
 *
 * Creates a new travel plan with destinations, dates, and budget.
 * Returns the travel plan, plan ID, and success message.
 *
 * @param args Input parameters (budget, destinations, endDate, preferences, startDate, title, travelers, userId).
 * @returns Promise resolving to travel plan creation results.
 */
export const createTravelPlan = createAiTool({
  description: "Create a new travel plan with destinations, dates, and budget.",
  execute: async (args) => {
    const redis = getRedis();
    if (!redis) return { error: "redis_unavailable", success: false } as const;
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const sessionUserId = auth?.user?.id;
    if (!sessionUserId) return { error: "unauthorized", success: false } as const;

    const planId = secureUuid();
    const now = nowIso();
    const plan: Plan = {
      budget: args.budget ?? null,
      components: {
        accommodations: [],
        activities: [],
        flights: [],
        notes: [],
        transportation: [],
      },
      createdAt: now,
      destinations: args.destinations,
      endDate: args.endDate,
      planId,
      preferences: args.preferences ?? {},
      startDate: args.startDate,
      status: "draft",
      title: args.title,
      travelers: args.travelers ?? 1,
      updatedAt: now,
      userId: sessionUserId,
    } as Plan;

    const valid = planSchema.safeParse(plan);
    if (!valid.success) {
      return { error: "invalid_plan_shape", success: false } as const;
    }

    const key = redisKeyForPlan(planId);
    try {
      await redis.set(key, valid.data);
      await redis.expire(key, TTL_DRAFT_SECONDS);
    } catch {
      return { error: "redis_set_failed", success: false } as const;
    }

    const mem = `Travel plan '${args.title}' created for user ${sessionUserId}`;
    await recordPlanMemory({
      content: mem,
      metadata: {
        budget: args.budget ?? null,
        destinations: args.destinations,
        endDate: args.endDate,
        planId,
        startDate: args.startDate,
        travelers: args.travelers ?? 1,
        type: "travelPlan",
      },
      userId: sessionUserId,
    });

    return { message: "created", plan, planId, success: true } as const;
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      identifier: (params) => params.userId,
      limit: RATE_CREATE_PER_DAY,
      window: "1 d",
    },
  },
  inputSchema: createTravelPlanInputSchema,
  name: "createTravelPlan",
});

/**
 * Tool for updating fields of an existing travel plan.
 *
 * Updates fields of an existing travel plan.
 * Returns the updated travel plan, plan ID, and success message.
 *
 * @param args Input parameters (planId, updates, userId).
 * @returns Promise resolving to travel plan update results.
 */
export const updateTravelPlan = createAiTool({
  description: "Update fields of an existing travel plan.",
  execute: async ({ planId, updates }) => {
    const redis = getRedis();
    if (!redis) return { error: "redis_unavailable", success: false } as const;
    const key = redisKeyForPlan(planId);
    let plan: Record<string, unknown> | null = null;
    try {
      plan = (await redis.get(key)) as Record<string, unknown> | null;
    } catch {
      return { error: "redis_get_failed", success: false } as const;
    }
    if (!plan) return { error: `plan_not_found:${planId}`, success: false } as const;

    const parsedExisting = planSchema.safeParse(plan);
    if (!parsedExisting.success) {
      return { error: "invalid_plan_shape", success: false } as const;
    }

    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const sessionUserId = auth?.user?.id;
    if (!sessionUserId || (plan as { userId?: string }).userId !== sessionUserId) {
      return { error: "unauthorized", success: false } as const;
    }

    const next: Plan = {
      ...parsedExisting.data,
      ...updates,
      updatedAt: nowIso(),
    } as Plan;

    try {
      const valid = planSchema.safeParse(next);
      if (!valid.success)
        return { error: "invalid_plan_shape", success: false } as const;
      await redis.set(key, valid.data);
      const isFinalized =
        valid.data.status === "finalized" || Boolean(valid.data.finalizedAt);
      await redis.expire(key, isFinalized ? TTL_FINAL_SECONDS : TTL_DRAFT_SECONDS);
    } catch {
      return { error: "redis_set_failed", success: false } as const;
    }

    return { message: "updated", plan: next, planId, success: true } as const;
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      identifier: (params) => params.planId, // Rate limit per plan
      limit: RATE_UPDATE_PER_MIN,
      window: "1 m",
    },
  },
  inputSchema: updateTravelPlanInputSchema,
  name: "updateTravelPlan",
});

/**
 * Tool for combining flights, accommodations, activities, and destination info.
 *
 * Combines flights, accommodations, activities, and destination info.
 * Returns the combined results and success message.
 *
 * @param args Input parameters (flightResults, accommodationResults, activityResults, destinationInfo, startDate, endDate, userPreferences).
 * @returns Promise resolving to combined search results.
 */
export const combineSearchResults = createAiTool({
  description: "Combine flights, accommodations, activities, and destination info.",
  execute: (args) => {
    // biome-ignore lint/suspicious/noExplicitAny: Complex result structure
    const recommendations: any = { accommodations: [], activities: [], flights: [] };
    // biome-ignore lint/suspicious/noExplicitAny: Complex result structure
    const result: any = {
      destinationHighlights: [],
      recommendations,
      totalEstimatedCost: 0,
      travelTips: [],
    };

    const flights = Array.isArray(args.flightResults?.offers)
      ? args.flightResults?.offers
      : [];
    if (flights.length) {
      const sorted = [...flights].sort(
        // biome-ignore lint/suspicious/noExplicitAny: Flight data structure from API
        (a: any, b: any) => coerceFloat(a.total_amount) - coerceFloat(b.total_amount)
      );
      result.recommendations.flights = sorted.slice(0, 3);
      if (sorted[0]) result.totalEstimatedCost += coerceFloat(sorted[0].total_amount);
    }

    const accoms = Array.isArray(args.accommodationResults?.accommodations)
      ? args.accommodationResults?.accommodations
      : [];
    if (accoms.length) {
      result.recommendations.accommodations = accoms.slice(0, 3);
      let nights = 3;
      if (args.startDate && args.endDate) {
        const s = new Date(args.startDate);
        const e = new Date(args.endDate);
        const diff = Math.ceil((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24));
        nights = Number.isFinite(diff) && diff > 0 ? diff : 1;
      }
      if (accoms[0])
        result.totalEstimatedCost += coerceFloat(accoms[0].price_per_night) * nights;
    }

    return Promise.resolve({
      combinedResults: result,
      message: "combined",
      success: true,
    } as const);
  },
  inputSchema: combineSearchResultsInputSchema,
  name: "combineSearchResults",
});

/**
 * Tool for persisting a travel plan and optionally finalizing it.
 *
 * Persists a travel plan and optionally finalizes it.
 * Returns the success message, plan ID, status, and summary markdown.
 *
 * @param args Input parameters (planId, finalize).
 * @returns Promise resolving to travel plan persistence results.
 */
export const saveTravelPlan = createAiTool({
  description: "Persist a travel plan and optionally finalize it.",
  execute: async ({ planId, finalize }) => {
    const redis = getRedis();
    if (!redis) return { error: "redis_unavailable", success: false } as const;
    const key = redisKeyForPlan(planId);
    const plan = await redis.get(key);
    if (!plan) return { error: `plan_not_found:${planId}`, success: false } as const;

    const parsed = planSchema.safeParse(plan);
    if (!parsed.success)
      return { error: "invalid_plan_shape", success: false } as const;

    const next = { ...parsed.data, updatedAt: nowIso() } as Plan;
    if (finalize) {
      next.status = "finalized";
      next.finalizedAt = nowIso();
    }

    await redis.set(key, next);
    await redis.expire(key, finalize ? TTL_FINAL_SECONDS : TTL_DRAFT_SECONDS);

    return {
      message: finalize ? "finalized_and_saved" : "saved",
      planId,
      status: next.status,
      success: true,
      summaryMarkdown: toMarkdownSummary(next),
    } as const;
  },
  inputSchema: saveTravelPlanInputSchema,
  name: "saveTravelPlan",
});

/**
 * Tool for deleting an existing travel plan owned by the session user.
 *
 * Deletes an existing travel plan owned by the session user.
 * Requires user approval before deletion to prevent accidental data loss.
 * Returns the success message and plan ID.
 *
 * @param args Input parameters (planId, sessionId).
 * @returns Promise resolving to travel plan deletion results.
 */
export const deleteTravelPlan = createAiTool({
  description:
    "Delete an existing travel plan owned by the session user. Requires approval before execution.",
  execute: async ({ planId, sessionId }) => {
    const redis = getRedis();
    if (!redis) return { error: "redis_unavailable", success: false } as const;
    const key = redisKeyForPlan(planId);
    const plan = await redis.get(key);
    if (!plan) return { error: `plan_not_found:${planId}`, success: false } as const;

    const parsed = planSchema.safeParse(plan);
    if (!parsed.success)
      return { error: "invalid_plan_shape", success: false } as const;

    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth?.user?.id;
    if (!userId || parsed.data.userId !== userId)
      return { error: "unauthorized", success: false } as const;

    // Require user approval before deleting travel plan
    // Uses Redis-backed approval flow - throws "approval_required" if not approved
    const effectiveSessionId = sessionId ?? userId;
    try {
      await requireApproval("deleteTravelPlan", {
        idempotencyKey: planId,
        sessionId: effectiveSessionId,
      });
    } catch (err) {
      // Convert approval exception to graceful error response for AI tool interface
      const message = err instanceof Error ? err.message : "approval_required";
      const approvalMeta =
        err && typeof err === "object" && "meta" in err
          ? (err as { meta?: unknown }).meta
          : undefined;
      return { approval: approvalMeta, error: message, success: false } as const;
    }

    try {
      await redis.del(key);
      return { message: "deleted", planId, success: true } as const;
    } catch (err) {
      planningLogger.error("Failed to delete travel plan from redis", {
        err,
        key,
        planId,
      });
      return { error: "delete_failed", planId, success: false } as const;
    }
  },
  inputSchema: z.object({
    /** Plan ID to delete (required) */
    planId: UUID_V4,
    /** Session ID for approval flow (optional, defaults to user ID) */
    sessionId: z.string().optional(),
  }),
  name: "deleteTravelPlan",
});
