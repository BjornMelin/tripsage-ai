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
import { createUnifiedErrorResponse } from "@/lib/api/error-response";
import { withApiGuards } from "@/lib/api/factory";
import { bumpTag } from "@/lib/cache/tags";
import { ensureAdmin, scopeSchema } from "@/lib/config/helpers";
import { nowIso, secureId } from "@/lib/security/random";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

const uuidSchema = z.string().uuid();

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

export const POST = withApiGuards({
  auth: true,
  rateLimit: "config:agents:rollback",
  telemetry: "config.agents.rollback",
})(async (req: NextRequest, { user, supabase }, _data, routeContext) => {
  try {
    ensureAdmin(user);
    const url = new URL(req.url);
    const scopeResult = scopeSchema.safeParse(
      url.searchParams.get("scope") ?? undefined
    );
    if (!scopeResult.success) {
      return createUnifiedErrorResponse({
        err: scopeResult.error,
        error: "invalid_request",
        reason: "Invalid scope parameter",
        status: 400,
      });
    }
    const scope = scopeResult.data;
    const { agentType, versionId } = await routeContext.params;

    const parsedAgent = agentTypeSchema.safeParse(agentType);
    const parsedVersion = uuidSchema.safeParse(versionId);
    if (!parsedAgent.success || !parsedVersion.success) {
      return createUnifiedErrorResponse({
        error: "invalid_request",
        reason: "Invalid agent or version id",
        status: 400,
      });
    }

    const { data: versionRow, error: versionError } = await supabase
      .from("agent_config_versions")
      .select("config")
      .eq("id", parsedVersion.data)
      .eq("agent_type", parsedAgent.data)
      .maybeSingle();

    if (versionError) {
      return createUnifiedErrorResponse({
        err: versionError,
        error: "internal",
        reason: "Failed to load version",
        status: 500,
      });
    }
    if (!versionRow) {
      return createUnifiedErrorResponse({
        error: "not_found",
        reason: "Version not found",
        status: 404,
      });
    }

    const rollbackConfig = buildRollbackConfig(versionRow.config as AgentConfig, scope);

    const createdBy = (user as { id: string } | null)?.id ?? "system";
    const { data, error } = await supabase.rpc("agent_config_upsert", {
      p_agent_type: parsedAgent.data,
      p_config: rollbackConfig,
      p_created_by: createdBy,
      p_scope: scope,
      p_summary: "rollback",
    });

    if (error) {
      recordTelemetryEvent("agent_config.rollback_failed", {
        attributes: { agentType: parsedAgent.data, scope },
        level: "error",
      });
      return createUnifiedErrorResponse({
        err: error,
        error: "internal",
        reason: "Failed to rollback configuration",
        status: 500,
      });
    }

    const newVersionId = Array.isArray(data)
      ? (data[0] as { version_id?: string } | undefined)?.version_id
      : (data as { version_id?: string } | null | undefined)?.version_id;

    if (!newVersionId) {
      return createUnifiedErrorResponse({
        error: "internal",
        reason: "Missing version id from rollback",
        status: 500,
      });
    }

    await bumpTag("configuration");

    emitOperationalAlert("agent_config.rollback", {
      attributes: {
        agentType: parsedAgent.data,
        scope,
        userId: (user as { id: string } | null)?.id ?? "unknown",
        versionId: newVersionId,
      },
      severity: "warning",
    });

    return NextResponse.json({ config: rollbackConfig, versionId: newVersionId });
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
      reason: "Failed to rollback agent configuration",
      status: 500,
    });
  }
});
