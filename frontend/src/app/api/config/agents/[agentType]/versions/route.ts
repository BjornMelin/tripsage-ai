/**
 * @fileoverview Agent configuration version history API.
 * Route: GET /api/config/agents/[agentType]/versions
 */

import "server-only";

import { agentTypeSchema } from "@schemas/configuration";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseStringId, validateSchema } from "@/lib/api/route-helpers";
import { ensureAdmin, scopeSchema } from "@/lib/config/helpers";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const paginationSchema = z.object({
  cursor: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(50).default(20),
});

export const GET = withApiGuards({
  auth: true,
  rateLimit: "config:agents:versions",
  telemetry: "config.agents.versions",
})(
  async (
    req: NextRequest,
    { user, supabase },
    _data,
    routeContext: RouteParamsContext
  ) => {
    try {
      ensureAdmin(user);
      const agentTypeResult = await parseStringId(routeContext, "agentType");
      if ("error" in agentTypeResult) return agentTypeResult.error;
      const { id: agentType } = agentTypeResult;
      const agentValidation = validateSchema(agentTypeSchema, agentType);
      if ("error" in agentValidation) {
        return agentValidation.error;
      }

      const rawScope = req.nextUrl.searchParams.get("scope");
      const scopeValidation = validateSchema(
        scopeSchema,
        rawScope === null || rawScope.trim() === "" ? undefined : rawScope
      );
      if ("error" in scopeValidation) {
        return scopeValidation.error;
      }
      const scope = scopeValidation.data;

      const paginationValidation = validateSchema(paginationSchema, {
        cursor: req.nextUrl.searchParams.get("cursor") ?? undefined,
        limit: req.nextUrl.searchParams.get("limit") ?? undefined,
      });
      if ("error" in paginationValidation) {
        return paginationValidation.error;
      }
      const pagination = paginationValidation.data;

      const result = await withTelemetrySpan(
        "agent_config.list_versions",
        { attributes: { agentType: agentValidation.data, scope } },
        async () => {
          let query = supabase
            .from("agent_config_versions")
            .select("id, created_at, created_by, summary, scope")
            .eq("agent_type", agentValidation.data)
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
        return errorResponse({
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
        return errorResponse({
          err,
          error: "forbidden",
          reason: "Admin access required",
          status: 403,
        });
      }
      return errorResponse({
        err,
        error: "internal",
        reason: "Failed to load version history",
        status: 500,
      });
    }
  }
);
