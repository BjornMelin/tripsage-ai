/**
 * @fileoverview Agent configuration rollback API.
 * Route: POST /api/config/agents/[agentType]/rollback/[versionId]
 */

import "server-only";

import {
  type AgentConfig,
  agentTypeSchema,
  configurationAgentConfigSchema,
} from "@schemas/configuration";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  parseStringId,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import { bumpTag } from "@/lib/cache/tags";
import { ensureAdmin, scopeSchema } from "@/lib/config/helpers";
import { nowIso, secureId } from "@/lib/security/random";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

const uuidSchema = z.uuid();

/**
 * Builds a rollback configuration for an agent.
 *
 * @param existing - The existing agent configuration.
 * @param scope - The scope of the agent configuration.
 * @returns The rollback configuration.
 */
function buildRollbackConfig(existing: AgentConfig, scope: string): AgentConfig {
  const now = nowIso();
  return configurationAgentConfigSchema.parse({
    ...existing,
    agentType: existing.agentType,
    id: `v${Math.floor(Date.now() / 1000)}_${secureId(8)}`,
    scope,
    updatedAt: now,
  });
}

/**
 * POST /api/config/agents/[agentType]/rollback/[versionId]
 *
 * Rolls back an agent configuration to a previous version.
 * Only allows admins to rollback configurations.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "config:agents:rollback",
  telemetry: "config.agents.rollback",
})(
  async (
    req: NextRequest,
    { user, supabase },
    _data,
    routeContext: RouteParamsContext
  ) => {
    try {
      ensureAdmin(user);
      const userResult = requireUserId(user);
      if ("error" in userResult) return userResult.error;
      const { userId } = userResult;
      const url = new URL(req.url);
      const scopeValidation = validateSchema(
        scopeSchema,
        url.searchParams.get("scope") ?? undefined
      );
      if ("error" in scopeValidation) {
        return scopeValidation.error;
      }
      const scope = scopeValidation.data;
      // Extract and validate agentType from route params and catch any errors
      const agentTypeResult = await parseStringId(routeContext, "agentType");
      if ("error" in agentTypeResult) return agentTypeResult.error;
      const { id: agentType } = agentTypeResult;
      const versionIdResult = await parseStringId(routeContext, "versionId");
      if ("error" in versionIdResult) return versionIdResult.error;
      const { id: versionId } = versionIdResult;

      const agentValidation = validateSchema(agentTypeSchema, agentType);
      const versionValidation = validateSchema(uuidSchema, versionId);
      if ("error" in agentValidation) {
        return agentValidation.error;
      }
      if ("error" in versionValidation) {
        return versionValidation.error;
      }

      const { data: versionRow, error: versionError } = await supabase
        .from("agent_config_versions")
        .select("config")
        .eq("id", versionValidation.data)
        .eq("agent_type", agentValidation.data)
        .maybeSingle();

      if (versionError) {
        return errorResponse({
          err: versionError,
          error: "internal",
          reason: "Failed to load version",
          status: 500,
        });
      }
      if (!versionRow) {
        return errorResponse({
          error: "not_found",
          reason: "Version not found",
          status: 404,
        });
      }

      const rollbackConfig = buildRollbackConfig(
        versionRow.config as AgentConfig,
        scope
      );

      const createdBy = userId;
      const { data, error } = await supabase.rpc("agent_config_upsert", {
        p_agent_type: agentValidation.data,
        p_config: rollbackConfig,
        p_created_by: createdBy,
        p_scope: scope,
        p_summary: "rollback",
      });

      if (error) {
        recordTelemetryEvent("agent_config.rollback_failed", {
          attributes: { agentType: agentValidation.data, scope },
          level: "error",
        });
        return errorResponse({
          err: error,
          error: "internal",
          reason: "Failed to rollback configuration",
          status: 500,
        });
      }

      const newVersionId = Array.isArray(data) ? data[0]?.version_id : undefined;

      if (!newVersionId) {
        return errorResponse({
          error: "internal",
          reason: "Missing version id from rollback",
          status: 500,
        });
      }

      await bumpTag("configuration");

      emitOperationalAlert("agent_config.rollback", {
        attributes: {
          agentType: agentValidation.data,
          scope,
          userId,
          versionId: newVersionId,
        },
        severity: "warning",
      });

      return NextResponse.json({ config: rollbackConfig, versionId: newVersionId });
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
        reason: "Failed to rollback agent configuration",
        status: 500,
      });
    }
  }
);
