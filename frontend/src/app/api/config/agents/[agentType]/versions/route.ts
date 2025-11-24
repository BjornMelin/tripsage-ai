/**
 * @fileoverview Agent configuration version history API.
 * Route: GET /api/config/agents/[agentType]/versions
 */

import "server-only";

import { agentTypeSchema } from "@schemas/configuration";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { createUnifiedErrorResponse } from "@/lib/api/error-response";
import { withApiGuards } from "@/lib/api/factory";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const scopeSchema = z.string().min(1).default("global");
const paginationSchema = z.object({
  cursor: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(50).default(20),
});

function ensureAdmin(
  user: unknown
): asserts user is { id: string; app_metadata?: Record<string, unknown> } {
  const candidate = user as { app_metadata?: Record<string, unknown> } | null;
  if (!(candidate?.app_metadata && candidate.app_metadata.is_admin === true)) {
    throw Object.assign(new Error("forbidden"), { status: 403 });
  }
}

export const GET = withApiGuards({
  auth: true,
  telemetry: "config.agents.versions",
})(async (req: NextRequest, { user, supabase }, _data, routeContext) => {
  try {
    ensureAdmin(user);
    const { agentType } = await routeContext.params;
    const parsedAgent = agentTypeSchema.safeParse(agentType);
    if (!parsedAgent.success) {
      return createUnifiedErrorResponse({
        error: "invalid_request",
        reason: "Invalid agent type",
        status: 400,
      });
    }

    const parsedScope = scopeSchema.safeParse(
      req.nextUrl.searchParams.get("scope") ?? undefined
    );
    if (!parsedScope.success) {
      return createUnifiedErrorResponse({
        details: parsedScope.error.issues,
        error: "invalid_request",
        reason: "Invalid scope parameter",
        status: 400,
      });
    }
    const scope = parsedScope.data;

    const parsedPagination = paginationSchema.safeParse({
      cursor: req.nextUrl.searchParams.get("cursor") ?? undefined,
      limit: req.nextUrl.searchParams.get("limit") ?? undefined,
    });
    if (!parsedPagination.success) {
      return createUnifiedErrorResponse({
        details: parsedPagination.error.issues,
        error: "invalid_request",
        reason: "Invalid pagination parameters",
        status: 400,
      });
    }
    const pagination = parsedPagination.data;

    const result = await withTelemetrySpan(
      "agent_config.list_versions",
      { attributes: { agentType: parsedAgent.data, scope } },
      async () => {
        let query = supabase
          .from("agent_config_versions")
          .select("id, created_at, created_by, summary, scope")
          .eq("agent_type", parsedAgent.data)
          .eq("scope", scope)
          .order("created_at", { ascending: false })
          .limit(pagination.limit + 1);

        if (pagination.cursor) {
          query = query.lt("created_at", pagination.cursor);
        }

        return await query;
      }
    );

    const { data, error } = result;
    if (error) {
      return createUnifiedErrorResponse({
        err: error,
        error: "internal",
        reason: "Failed to list versions",
        status: 500,
      });
    }

    const hasMore = (data?.length ?? 0) > pagination.limit;
    const versions = (data ?? []).slice(0, pagination.limit).map((row) => ({
      createdAt: row.created_at,
      createdBy: row.created_by,
      id: row.id,
      scope: row.scope,
      summary: row.summary,
    }));

    return NextResponse.json({
      nextCursor: hasMore ? data?.[pagination.limit]?.created_at : undefined,
      versions,
    });
  } catch (err) {
    if ((err as { status?: number }).status === 403) {
      return createUnifiedErrorResponse({
        err,
        error: "forbidden",
        reason: "Admin access required",
        status: 403,
      });
    }
    return createUnifiedErrorResponse({
      err,
      error: "internal",
      reason: "Failed to load version history",
      status: 500,
    });
  }
});
