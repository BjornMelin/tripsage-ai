/**
 * @fileoverview Travel planning tools implemented with AI SDK v6.
 * Server-only execution with Redis persistence and optional memory logging.
 */
import "server-only";

import { tool } from "ai";
import { z } from "zod";
import { getRedis } from "@/lib/redis";
import { nowIso, secureUuid } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import {
  RATE_CREATE_PER_DAY,
  RATE_UPDATE_PER_MIN,
  TTL_DRAFT_SECONDS,
  TTL_FINAL_SECONDS,
} from "./constants";
import { type Plan, planSchema } from "./planning.schema";

// Internal helpers and schemas (not exported)

const UUI_DV4 = z.uuid();
// Use Zod v4 ISO date validator - validates ISO 8601 date format (YYYY-MM-DD)
const ISO_DATE = z.iso.date({ error: "must be YYYY-MM-DD" });
const PREFERENCES = z.record(z.string(), z.unknown()).default({});

export const combineSearchResultsInputSchema = z.object({
  accommodationResults: z.record(z.string(), z.unknown()).optional(),
  activityResults: z.record(z.string(), z.unknown()).optional(),
  destinationInfo: z.record(z.string(), z.unknown()).optional(),
  endDate: ISO_DATE.optional(),
  flightResults: z.record(z.string(), z.unknown()).optional(),
  startDate: ISO_DATE.optional(),
  userPreferences: z.record(z.string(), z.unknown()).optional(),
});

export const createTravelPlanInputSchema = z.object({
  budget: z.number().min(0).optional(),
  destinations: z.array(z.string().min(1)).min(1),
  endDate: ISO_DATE,
  preferences: PREFERENCES.optional(),
  startDate: ISO_DATE,
  title: z.string().min(1, { error: "title required" }),
  travelers: z.int().min(1).max(50).default(1),
  userId: z.string().min(1).optional(),
});

export const saveTravelPlanInputSchema = z.object({
  finalize: z.boolean().default(false).optional(),
  planId: UUI_DV4,
  userId: z.string().min(1).optional(),
});
type PlanComponents = Plan["components"];

function redisKeyForPlan(planId: string): string {
  return `travel_plan:${planId}`;
}

function coerceFloat(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function read<T = unknown>(obj: unknown, key: string): T | undefined {
  if (obj && typeof obj === "object" && key in (obj as Record<string, unknown>)) {
    return (obj as Record<string, unknown>)[key] as T;
  }
  return undefined;
}

async function recordPlanMemory(opts: {
  userId: string;
  content: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  try {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const sessionUserId = auth?.user?.id;
    if (!sessionUserId || sessionUserId !== opts.userId) return; // degrade silently
    type LooseFrom = {
      from: (table: string) => {
        insert: (values: unknown) => {
          select: (cols: string) => {
            single: () => Promise<{ data: unknown; error: unknown }>;
          };
        };
      };
    };
    const sb = supabase as unknown as LooseFrom;
    await sb
      .from("memories")
      .insert({
        content: opts.content,
        // biome-ignore lint/style/useNamingConvention: database column names use snake_case
        memory_type: "conversation_context",
        metadata: opts.metadata ?? {},
        // biome-ignore lint/style/useNamingConvention: database column names use snake_case
        user_id: sessionUserId,
      })
      .select("id")
      .single();
  } catch {
    // no-op; memory logging is best-effort only
  }
}

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

  const accommodations = components.accommodations ?? [];
  if (accommodations.length) {
    md += "## Accommodations\n\n";
    accommodations.forEach((a, i) => {
      md += `### ${String((read(a, "name") as string) ?? `Accommodation ${i + 1}`)}\n\n`;
      md += `* **Location**: ${String(read(a, "location") ?? "N/A")}\n`;
      md += `* **Check-in**: ${String(read(a, "checkInDate") ?? "N/A")}\n`;
      md += `* **Check-out**: ${String(read(a, "checkOutDate") ?? "N/A")}\n`;
      md += `* **Price**: $${String(read(a, "pricePerNight") ?? "N/A")} per night\n\n`;
    });
  }

  const activities = components.activities ?? [];
  if (activities.length) {
    md += "## Activities\n\n";
    activities.forEach((a, i) => {
      md += `### ${String((read(a, "name") as string) ?? `Activity ${i + 1}`)}\n\n`;
      md += `* **Location**: ${String(read(a, "location") ?? "N/A")}\n`;
      md += `* **Date**: ${String(read(a, "date") ?? "N/A")}\n`;
      md += `* **Price**: $${String(read(a, "pricePerPerson") ?? "N/A")} per person\n\n`;
    });
  }
  return md;
}

export const createTravelPlan = tool({
  description: "Create a new travel plan with destinations, dates, and budget.",
  execute: async (args) => {
    return await withTelemetrySpan(
      "planning.createTravelPlan",
      {
        attributes: {
          destinationsCount: args.destinations.length,
          hasBudget: typeof args.budget === "number",
          travelers: args.travelers ?? 1,
        },
      },
      async (span) => {
        const redis = getRedis();
        if (!redis) return { error: "redis_unavailable", success: false } as const;
        const supabase = await createServerSupabase();
        const { data: auth } = await supabase.auth.getUser();
        const sessionUserId = auth?.user?.id;
        if (!sessionUserId) return { error: "unauthorized", success: false } as const;

        // Update span with userId after auth check
        span.setAttribute("userId", sessionUserId);

        const planId = secureUuid();
        const now = nowIso();
        const components: PlanComponents = {
          accommodations: [],
          activities: [],
          flights: [],
          notes: [],
          transportation: [],
        };
        const plan: Plan = {
          budget: args.budget ?? null,
          components,
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

        // Per-user daily create rate limit (20/day). Degrade gracefully on failure.
        try {
          const day = new Date().toISOString().slice(0, 10).replaceAll("-", "");
          const rlKey = `travel_plan:rate:create:${sessionUserId}:${day}`;
          const count = await redis.incr(rlKey);
          if (typeof count === "number" && count === 1) {
            await redis.expire(rlKey, 86400);
          }
          if (typeof count === "number" && count > RATE_CREATE_PER_DAY) {
            if (process.env.NODE_ENV !== "test") {
              span.addEvent("rate_limited", { event: "create", key: rlKey });
            }
            return { error: "rate_limited_plan_create", success: false } as const;
          }
        } catch {
          // ignore rate limiter failures
        }

        // Validate plan before persist
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

        const mem =
          `Travel plan '${args.title}' created for user ${sessionUserId} with destinations: ${args.destinations.join(", ")} from ${args.startDate} to ${args.endDate} for ${args.travelers} travelers` +
          (typeof args.budget === "number" ? ` with budget $${args.budget}` : "");
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
      }
    );
  },
  inputSchema: createTravelPlanInputSchema,
});

export const updateTravelPlan = tool({
  description: "Update fields of an existing travel plan.",
  execute: async ({ planId, userId: _ignored, updates }) => {
    return await withTelemetrySpan(
      "planning.updateTravelPlan",
      {
        attributes: {
          planId,
        },
      },
      async (span) => {
        const redis = getRedis();
        if (!redis) return { error: "redis_unavailable", success: false } as const;
        const key = redisKeyForPlan(planId);
        let plan: Record<string, unknown> | null = null;
        try {
          plan = (await redis.get(key)) as Record<string, unknown> | null;
        } catch {
          return { error: "redis_get_failed", success: false } as const;
        }
        if (!plan)
          return { error: `plan_not_found:${planId}`, success: false } as const;
        const parsedExisting = planSchema.safeParse(plan);
        if (!parsedExisting.success) {
          return { error: "invalid_plan_shape", success: false } as const;
        }
        const supabase = await createServerSupabase();
        const { data: auth } = await supabase.auth.getUser();
        const sessionUserId = auth?.user?.id;
        if (!sessionUserId) return { error: "unauthorized", success: false } as const;
        if ((plan as { userId?: string }).userId !== sessionUserId)
          return { error: "unauthorized", success: false } as const;

        const UpdateSchema = z.strictObject({
          budget: z.number().min(0).nullable().optional(),
          destinations: z.array(z.string().min(1)).min(1).optional(),
          endDate: ISO_DATE.optional(),
          preferences: PREFERENCES.optional(),
          startDate: ISO_DATE.optional(),
          title: z.string().min(1).optional(),
          travelers: z.int().min(1).max(50).optional(),
        });
        const parsed = UpdateSchema.safeParse(updates ?? {});
        if (!parsed.success) {
          return {
            error: `invalid_updates:${parsed.error.issues.map((i) => i.path.join(".")).join(",")}`,
            success: false,
          } as const;
        }
        const applied: string[] = [];
        const next: Plan = { ...parsedExisting.data } as Plan;
        for (const [k, v] of Object.entries(parsed.data)) {
          (next as unknown as Record<string, unknown>)[k] = v as unknown;
          applied.push(k);
        }
        next.updatedAt = nowIso();

        // Update span with changesCount
        span.setAttribute("changesCount", applied.length);

        // Per-plan per-minute update limiter (60/min). Degrade on failure.
        try {
          const rlKey = `travel_plan:rate:update:${planId}`;
          const count = await redis.incr(rlKey);
          if (typeof count === "number" && count === 1) {
            await redis.expire(rlKey, 60);
          }
          if (typeof count === "number" && count > RATE_UPDATE_PER_MIN) {
            if (process.env.NODE_ENV !== "test") {
              span.addEvent("rate_limited", { event: "update", key: rlKey, planId });
            }
            return { error: "rate_limited_plan_update", success: false } as const;
          }
        } catch {
          // ignore
        }

        try {
          // Validate write
          const valid = planSchema.safeParse(next);
          if (!valid.success) {
            return { error: "invalid_plan_shape", success: false } as const;
          }
          await redis.set(key, valid.data);
          const isFinalized =
            valid.data.status === "finalized" || Boolean(valid.data.finalizedAt);
          await redis.expire(key, isFinalized ? TTL_FINAL_SECONDS : TTL_DRAFT_SECONDS);
        } catch {
          return { error: "redis_set_failed", success: false } as const;
        }

        if (applied.length) {
          const detail = applied.map((k) => `${k} changed`).join(", ");
          await recordPlanMemory({
            content: `Travel plan '${String(next.title ?? "Untitled")}' updated with changes: ${detail}`,
            metadata: { changes: parsed.data, planId, type: "travelPlanUpdate" },
            userId: sessionUserId,
          });
        }

        return { message: "updated", plan: next, planId, success: true } as const;
      }
    );
  },
  inputSchema: z.object({
    planId: UUI_DV4,
    updates: z.record(z.string(), z.unknown()),
    userId: z.string().min(1).optional(),
  }),
});

export const combineSearchResults = tool({
  description:
    "Combine flights, accommodations, activities, and destination info into unified recommendations.",
  execute: (args) => {
    const recommendations: {
      flights: Array<Record<string, unknown>>;
      accommodations: Array<Record<string, unknown>>;
      activities: Array<Record<string, unknown>>;
    } = { accommodations: [], activities: [], flights: [] };

    const result: {
      recommendations: typeof recommendations;
      totalEstimatedCost: number;
      destinationHighlights: string[];
      travelTips: string[];
    } = {
      destinationHighlights: [],
      recommendations,
      totalEstimatedCost: 0,
      travelTips: [],
    };

    const flights = Array.isArray(args.flightResults?.offers)
      ? (args.flightResults?.offers as Array<Record<string, unknown>>)
      : [];
    if (flights.length) {
      const sorted = [...flights].sort(
        (a, b) => coerceFloat(a.total_amount) - coerceFloat(b.total_amount)
      );
      result.recommendations.flights = sorted.slice(0, 3);
      if (sorted[0]) result.totalEstimatedCost += coerceFloat(sorted[0].total_amount);
    }

    const accoms = Array.isArray(args.accommodationResults?.accommodations)
      ? (args.accommodationResults?.accommodations as Array<Record<string, unknown>>)
      : [];
    if (accoms.length) {
      const withScore = accoms.map((a) => {
        const rec = a as Record<string, unknown>;
        return {
          ...rec,
          _score:
            coerceFloat(rec.price_per_night) * -0.7 + coerceFloat(rec.rating) * 0.3,
        } as Record<string, unknown> & { _score: number };
      });
      const sorted = withScore.sort(
        (a, b) => coerceFloat(b._score) - coerceFloat(a._score)
      );
      // Strip internal _score before returning
      result.recommendations.accommodations = sorted.slice(0, 3).map((item) => {
        const { _score, ...rest } = item;
        return rest;
      });
      // nights: derive from provided dates or default to 3
      let nights = 3;
      if (args.startDate && args.endDate) {
        const s = new Date(args.startDate);
        const e = new Date(args.endDate);
        const diff = Math.ceil((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24));
        nights = Number.isFinite(diff) && diff > 0 ? diff : 1;
      }
      if (sorted[0])
        result.totalEstimatedCost += coerceFloat(sorted[0].price_per_night) * nights;
    }

    const activities = Array.isArray(args.activityResults?.activities)
      ? (args.activityResults?.activities as Array<Record<string, unknown>>)
      : [];
    if (activities.length) {
      const sorted = [...activities].sort(
        (a, b) => coerceFloat(b.rating) - coerceFloat(a.rating)
      );
      result.recommendations.activities = sorted.slice(0, 5);
      for (const a of sorted.slice(0, 3)) {
        result.totalEstimatedCost += coerceFloat(a.price_per_person);
      }
    }

    const info = (args.destinationInfo ?? {}) as Record<string, unknown>;
    const highlightsRaw = Array.isArray(info.highlights)
      ? (info.highlights as unknown[])
      : [];
    if (highlightsRaw.length) {
      result.destinationHighlights = highlightsRaw.slice(0, 5).map((x) => String(x));
    }
    const tipsRaw = Array.isArray(info.tips) ? (info.tips as unknown[]) : [];
    if (tipsRaw.length) {
      result.travelTips = tipsRaw.slice(0, 3).map((x) => String(x));
    }

    return { combinedResults: result, message: "combined", success: true } as const;
  },
  inputSchema: combineSearchResultsInputSchema,
});

export const saveTravelPlan = tool({
  description: "Persist a travel plan and optionally finalize it (extends TTL).",
  execute: async ({ planId, userId: _ignored, finalize }) => {
    return await withTelemetrySpan(
      "planning.saveTravelPlan",
      {
        attributes: {
          finalize: Boolean(finalize),
          planId,
        },
      },
      async (_span) => {
        const redis = getRedis();
        if (!redis) return { error: "redis_unavailable", success: false } as const;
        const key = redisKeyForPlan(planId);
        let plan: Record<string, unknown> | null = null;
        try {
          plan = (await redis.get(key)) as Record<string, unknown> | null;
        } catch {
          return { error: "redis_get_failed", success: false } as const;
        }
        if (!plan)
          return { error: `plan_not_found:${planId}`, success: false } as const;
        const parsedExisting = planSchema.safeParse(plan);
        if (!parsedExisting.success) {
          return { error: "invalid_plan_shape", success: false } as const;
        }
        const supabase = await createServerSupabase();
        const { data: auth } = await supabase.auth.getUser();
        const sessionUserId = auth?.user?.id;
        if (!sessionUserId) return { error: "unauthorized", success: false } as const;
        if ((plan as { userId?: string }).userId !== sessionUserId)
          return { error: "unauthorized", success: false } as const;

        const now = nowIso();
        const next: Plan = { ...parsedExisting.data, updatedAt: now } as Plan;
        if (finalize) {
          next.status = "finalized";
          next.finalizedAt = now;
        }

        try {
          const valid = planSchema.safeParse(next);
          if (!valid.success)
            return { error: "invalid_plan_shape", success: false } as const;
          await redis.set(key, valid.data);
          await redis.expire(key, finalize ? TTL_FINAL_SECONDS : TTL_DRAFT_SECONDS);
        } catch {
          return { error: "redis_set_failed", success: false } as const;
        }

        if (finalize) {
          await recordPlanMemory({
            content: `Travel plan '${String(next.title ?? "Untitled")}' finalized on ${now}`,
            metadata: { finalizedAt: now, planId, type: "travelPlanFinalization" },
            userId: sessionUserId,
          });
        }

        const comps =
          (next.components as PlanComponents | undefined) ??
          ({
            accommodations: [],
            activities: [],
            flights: [],
            notes: [],
            transportation: [],
          } as PlanComponents);
        const counts = [
          ["flights", comps.flights?.length ?? 0],
          ["accommodations", comps.accommodations?.length ?? 0],
          ["activities", comps.activities?.length ?? 0],
          ["transportation", comps.transportation?.length ?? 0],
          ["notes", comps.notes?.length ?? 0],
        ] as const;
        const present = counts.filter(([, n]) => (n as number) > 0);
        if (present.length) {
          const summary = `Travel plan includes: ${present
            .map(([k, n]) => `${n} ${k}`)
            .join(", ")}`;
          await recordPlanMemory({
            content: summary,
            metadata: { components: comps, planId, type: "travelPlanComponents" },
            userId: sessionUserId,
          });
        }

        return {
          message: finalize ? "finalized_and_saved" : "saved",
          planId,
          status: next.status ?? "draft",
          success: true,
          summaryMarkdown: toMarkdownSummary(next),
        } as const;
      }
    );
  },
  inputSchema: saveTravelPlanInputSchema,
});

export const deleteTravelPlan = tool({
  description: "Delete an existing travel plan owned by the session user.",
  execute: async ({ planId }) => {
    return await withTelemetrySpan(
      "planning.deleteTravelPlan",
      {
        attributes: {
          planId,
        },
      },
      async (span) => {
        const redis = getRedis();
        if (!redis) return { error: "redis_unavailable", success: false } as const;
        const key = redisKeyForPlan(planId);
        let plan: Record<string, unknown> | null = null;
        try {
          plan = (await redis.get(key)) as Record<string, unknown> | null;
        } catch {
          return { error: "redis_get_failed", success: false } as const;
        }
        if (!plan)
          return { error: `plan_not_found:${planId}`, success: false } as const;
        const parsed = planSchema.safeParse(plan);
        if (!parsed.success)
          return { error: "invalid_plan_shape", success: false } as const;
        const supabase = await createServerSupabase();
        const { data: auth } = await supabase.auth.getUser();
        const sessionUserId = auth?.user?.id;
        if (!sessionUserId) return { error: "unauthorized", success: false } as const;
        if (parsed.data.userId !== sessionUserId)
          return { error: "unauthorized", success: false } as const;

        // Update span with userId after auth check
        span.setAttribute("userId", sessionUserId);

        try {
          await redis.del(key);
        } catch {
          return { error: "redis_delete_failed", success: false } as const;
        }
        await recordPlanMemory({
          content: "Travel plan deleted",
          metadata: { planId, type: "travelPlanDeleted" },
          userId: sessionUserId,
        });
        return { message: "deleted", planId, success: true } as const;
      }
    );
  },
  inputSchema: z.object({ planId: UUI_DV4, userId: z.string().optional() }),
});
