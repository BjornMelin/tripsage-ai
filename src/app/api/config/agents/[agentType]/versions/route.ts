/**
 * @fileoverview Agent configuration version history API. Route: GET /api/config/agents/[agentType]/versions
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
import { getMany } from "@/lib/supabase/typed-helpers";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const paginationSchema = z.object({
  cursor: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(50).default(20),
});

const parseScopeParam = (raw: string | null) =>
  validateSchema(scopeSchema, raw ?? undefined);

/**
 * Lists version history for an agent configuration.
 *
 * Requires admin authentication. Supports cursor-based pagination.
 *
 * @param req - NextRequest with optional scope, cursor, and limit query params.
 * @returns Promise resolving to paginated version list with nextCursor.
 * @see docs/architecture/decisions/adr-0052-agent-configuration-backend.md
 */
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
      if (!agentTypeResult.ok) return agentTypeResult.error;
      const agentType = agentTypeResult.data;
      const agentValidation = validateSchema(agentTypeSchema, agentType);
      if (!agentValidation.ok) return agentValidation.error;

      const scopeResult = parseScopeParam(req.nextUrl.searchParams.get("scope"));
      if (!scopeResult.ok) return scopeResult.error;
      const scope = scopeResult.data;

      const paginationValidation = validateSchema(paginationSchema, {
        cursor: req.nextUrl.searchParams.get("cursor") ?? undefined,
        limit: req.nextUrl.searchParams.get("limit") ?? undefined,
      });
      if (!paginationValidation.ok) return paginationValidation.error;
      const pagination = paginationValidation.data;

      const result = await withTelemetrySpan(
        "agent_config.list_versions",
        { attributes: { agentType: agentValidation.data, scope } },
        async () => {
          return await getMany(
            supabase,
            "agent_config_versions",
            (qb) => {
              let filtered = qb
                .eq("agent_type", agentValidation.data)
                .eq("scope", scope);
              if (pagination.cursor) {
                filtered = filtered.lt("created_at", pagination.cursor);
              }
              return filtered;
            },
            {
              ascending: false,
              limit: pagination.limit + 1,
              orderBy: "created_at",
              select: "id, created_at, created_by, summary, scope",
              validate: false,
            }
          );
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
