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

// Internal helpers and schemas (not exported)

const UUI_DV4 = z.string().uuid();

const ISO_DATE = z.string().regex(/^\d{4}-\d{2}-\d{2}$/u, "must be YYYY-MM-DD");

const PREFERENCES = z.record(z.string(), z.unknown()).default({});

const COMPONENTS_SCHEMA = z.object({
  accommodations: z.array(z.record(z.string(), z.unknown())).default([]),
  activities: z.array(z.record(z.string(), z.unknown())).default([]),
  flights: z.array(z.record(z.string(), z.unknown())).default([]),
  notes: z.array(z.record(z.string(), z.unknown())).default([]),
  transportation: z.array(z.record(z.string(), z.unknown())).default([]),
});

type PlanComponents = z.infer<typeof COMPONENTS_SCHEMA>;

function redisKeyForPlan(planId: string): string {
  return `travel_plan:${planId}`;
}

function coerceFloat(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
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

function toMarkdownSummary(plan: Record<string, unknown>): string {
  const title = String(plan.title ?? "Travel Plan");
  const destinations = (plan.destinations as string[] | undefined) ?? [];
  const start = String((plan as { startDate?: string }).startDate ?? "");
  const end = String((plan as { endDate?: string }).endDate ?? "");
  const travelers = Number(plan.travelers ?? 1);
  const budget = plan.budget as number | undefined;
  const components = (plan.components as PlanComponents | undefined) ?? {
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
    flights.forEach((fRaw, i) => {
      const f = fRaw as Record<string, unknown>;
      md += `### Flight ${i + 1}\n\n`;
      md += `* **From**: ${String(f.origin ?? "N/A")}\n`;
      md += `* **To**: ${String(f.destination ?? "N/A")}\n`;
      // biome-ignore lint/style/useNamingConvention: allow fallback to legacy key if present
      md += `* **Date**: ${String((f as { departureDate?: string }).departureDate ?? (f as { departure_date?: string }).departure_date ?? "N/A")}\n`;
      md += `* **Airline**: ${String(f.airline ?? "N/A")}\n`;
      // biome-ignore lint/style/useNamingConvention: allow fallback to legacy key if present
      md += `* **Price**: $${String((f as { price?: unknown }).price ?? (f as { total_amount?: unknown }).total_amount ?? "N/A")}\n\n`;
    });
  }

  const accommodations = components.accommodations ?? [];
  if (accommodations.length) {
    md += "## Accommodations\n\n";
    accommodations.forEach((aRaw, i) => {
      const a = aRaw as Record<string, unknown>;
      md += `### ${String(a.name ?? `Accommodation ${i + 1}`)}\n\n`;
      md += `* **Location**: ${String(a.location ?? "N/A")}\n`;
      // biome-ignore lint/style/useNamingConvention: allow fallback to legacy key if present
      md += `* **Check-in**: ${String((a as { checkInDate?: string }).checkInDate ?? (a as { check_in_date?: string }).check_in_date ?? "N/A")}\n`;
      // biome-ignore lint/style/useNamingConvention: allow fallback to legacy key if present
      md += `* **Check-out**: ${String((a as { checkOutDate?: string }).checkOutDate ?? (a as { check_out_date?: string }).check_out_date ?? "N/A")}\n`;
      // biome-ignore lint/style/useNamingConvention: allow fallback to legacy key if present
      md += `* **Price**: $${String((a as { pricePerNight?: unknown }).pricePerNight ?? (a as { price_per_night?: unknown }).price_per_night ?? "N/A")} per night\n\n`;
    });
  }

  const activities = components.activities ?? [];
  if (activities.length) {
    md += "## Activities\n\n";
    activities.forEach((aRaw, i) => {
      const a = aRaw as Record<string, unknown>;
      md += `### ${String(a.name ?? `Activity ${i + 1}`)}\n\n`;
      md += `* **Location**: ${String(a.location ?? "N/A")}\n`;
      md += `* **Date**: ${String((a as { date?: string }).date ?? "N/A")}\n`;
      // biome-ignore lint/style/useNamingConvention: allow fallback to legacy key if present
      md += `* **Price**: $${String((a as { pricePerPerson?: unknown }).pricePerPerson ?? (a as { price_per_person?: unknown }).price_per_person ?? "N/A")} per person\n\n`;
    });
  }
  return md;
}

export const createTravelPlan = tool({
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
    const components: PlanComponents = {
      accommodations: [],
      activities: [],
      flights: [],
      notes: [],
      transportation: [],
    };
    const plan = {
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
    } satisfies Record<string, unknown>;

    const key = redisKeyForPlan(planId);
    try {
      await redis.set(key, plan);
      await redis.expire(key, 86400 * 7); // 7 days
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
  },
  inputSchema: z.object({
    budget: z.number().min(0).optional(),
    destinations: z.array(z.string().min(1)).min(1),
    endDate: ISO_DATE,
    preferences: PREFERENCES.optional(),
    startDate: ISO_DATE,
    title: z.string().min(1, "title required"),
    travelers: z.number().int().min(1).max(50).default(1),
    userId: z.string().min(1).optional(),
  }),
});

export const updateTravelPlan = tool({
  description: "Update fields of an existing travel plan.",
  execute: async ({ planId, userId: _ignored, updates }) => {
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
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const sessionUserId = auth?.user?.id;
    if (!sessionUserId) return { error: "unauthorized", success: false } as const;
    if ((plan as { userId?: string }).userId !== sessionUserId)
      return { error: "unauthorized", success: false } as const;

    const UpdateSchema = z
      .object({
        budget: z.number().min(0).nullable().optional(),
        destinations: z.array(z.string().min(1)).min(1).optional(),
        endDate: ISO_DATE.optional(),
        preferences: PREFERENCES.optional(),
        startDate: ISO_DATE.optional(),
        title: z.string().min(1).optional(),
        travelers: z.number().int().min(1).max(50).optional(),
      })
      .strict();
    const parsed = UpdateSchema.safeParse(updates ?? {});
    if (!parsed.success) {
      return {
        error: `invalid_updates:${parsed.error.issues.map((i) => i.path.join(".")).join(",")}`,
        success: false,
      } as const;
    }
    const applied: string[] = [];
    for (const [k, v] of Object.entries(parsed.data)) {
      (plan as Record<string, unknown>)[k] = v as unknown;
      applied.push(k);
    }
    (plan as { updatedAt?: string }).updatedAt = nowIso();

    try {
      await redis.set(key, plan);
      const isFinalized =
        (plan as { status?: string }).status === "finalized" ||
        Boolean((plan as { finalizedAt?: string }).finalizedAt);
      await redis.expire(key, isFinalized ? 86400 * 30 : 86400 * 7);
    } catch {
      return { error: "redis_set_failed", success: false } as const;
    }

    if (applied.length) {
      const detail = applied.map((k) => `${k} changed`).join(", ");
      await recordPlanMemory({
        content: `Travel plan '${String(plan.title ?? "Untitled")}' updated with changes: ${detail}`,
        metadata: { changes: parsed.data, planId, type: "travelPlanUpdate" },
        userId: sessionUserId,
      });
    }

    return { message: "updated", plan, planId, success: true } as const;
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
      result.recommendations.accommodations = sorted.slice(0, 3);
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
  inputSchema: z.object({
    accommodationResults: z.record(z.string(), z.unknown()).optional(),
    activityResults: z.record(z.string(), z.unknown()).optional(),
    destinationInfo: z.record(z.string(), z.unknown()).optional(),
    endDate: ISO_DATE.optional(),
    flightResults: z.record(z.string(), z.unknown()).optional(),
    startDate: ISO_DATE.optional(),
    userPreferences: z.record(z.string(), z.unknown()).optional(),
  }),
});

export const saveTravelPlan = tool({
  description: "Persist a travel plan and optionally finalize it (extends TTL).",
  execute: async ({ planId, userId: _ignored, finalize }) => {
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
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const sessionUserId = auth?.user?.id;
    if (!sessionUserId) return { error: "unauthorized", success: false } as const;
    if ((plan as { userId?: string }).userId !== sessionUserId)
      return { error: "unauthorized", success: false } as const;

    const now = nowIso();
    (plan as { updatedAt?: string }).updatedAt = now;
    if (finalize) {
      (plan as { status?: string }).status = "finalized";
      (plan as { finalizedAt?: string }).finalizedAt = now;
    }

    try {
      await redis.set(key, plan);
      await redis.expire(key, finalize ? 86400 * 30 : 86400 * 7);
    } catch {
      return { error: "redis_set_failed", success: false } as const;
    }

    if (finalize) {
      await recordPlanMemory({
        content: `Travel plan '${String(plan.title ?? "Untitled")}' finalized on ${now}`,
        metadata: { finalizedAt: now, planId, type: "travelPlanFinalization" },
        userId: sessionUserId,
      });
    }

    const comps = ((plan.components as PlanComponents | undefined) ?? {
      accommodations: [],
      activities: [],
      flights: [],
      notes: [],
      transportation: [],
    }) as PlanComponents;
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
      status: (plan as Record<string, unknown>).status ?? "draft",
      success: true,
      summaryMarkdown: toMarkdownSummary(plan),
    } as const;
  },
  inputSchema: z.object({
    finalize: z.boolean().default(false).optional(),
    planId: UUI_DV4,
    userId: z.string().min(1).optional(),
  }),
});
