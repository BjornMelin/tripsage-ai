/**
 * @fileoverview Agent configuration read/update API.
 * Routes: GET/PUT /api/config/agents/[agentType]
 * - Authenticated admin-only via RLS + explicit check.
 * - GET resolves active config (cached) via resolver.
 * - PUT validates input, builds config payload, upserts via Supabase function, and bumps cache tags.
 */

import "server-only";

import {
  type AgentConfig,
  type AgentType,
  agentConfigRequestSchema,
  agentTypeSchema,
  configurationAgentConfigSchema,
} from "@schemas/configuration";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { z } from "zod";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  parseJsonBody,
  parseStringId,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import { bumpTag } from "@/lib/cache/tags";
import { ensureAdmin, scopeSchema } from "@/lib/config/helpers";
import { nowIso, secureId } from "@/lib/security/random";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";

const configUpdateBodySchema = agentConfigRequestSchema.strict();

const parseScopeParam = (raw: string | null) =>
  validateSchema(scopeSchema, raw ?? undefined);

function buildConfigPayload(
  agentType: AgentType,
  scope: string,
  body: z.infer<typeof configUpdateBodySchema>,
  existing?: AgentConfig
): AgentConfig {
  const now = nowIso();
  const baseConfigId =
    existing?.id ?? `v${Math.floor(Date.now() / 1000)}_${secureId(8)}`;
  const effectiveModel = body.model ?? existing?.model ?? "gpt-4o";
  return configurationAgentConfigSchema.parse({
    agentType,
    createdAt: existing?.createdAt ?? now,
    id: baseConfigId,
    model: effectiveModel,
    parameters: {
      description: body.description ?? existing?.parameters.description,
      maxTokens: body.maxTokens ?? existing?.parameters.maxTokens,
      model: effectiveModel,
      temperature: body.temperature ?? existing?.parameters.temperature,
      timeoutSeconds: body.timeoutSeconds ?? existing?.parameters.timeoutSeconds,
      topP: body.topP ?? existing?.parameters.topP,
    },
    scope,
    updatedAt: now,
  });
}

export const GET = withApiGuards({
  auth: true,
  rateLimit: "config:agents:read",
  telemetry: "config.agents.get",
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
      const scopeResult = parseScopeParam(req.nextUrl.searchParams.get("scope"));
      if ("error" in scopeResult) return scopeResult.error;
      const scope = scopeResult.data;
      const result = await resolveAgentConfig(agentValidation.data, {
        scope,
        supabase,
      });
      return NextResponse.json(result);
    } catch (err) {
      if ((err as { status?: number }).status === 404) {
        return errorResponse({
          err,
          error: "not_found",
          reason: "Agent configuration not found",
          status: 404,
        });
      }
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
        reason: "Failed to load agent configuration",
        status: 500,
      });
    }
  }
);

export const PUT = withApiGuards({
  auth: true,
  rateLimit: "config:agents:update",
  telemetry: "config.agents.update",
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
      const agentTypeResult = await parseStringId(routeContext, "agentType");
      if ("error" in agentTypeResult) return agentTypeResult.error;
      const { id: agentType } = agentTypeResult;
      const agentValidation = validateSchema(agentTypeSchema, agentType);
      if ("error" in agentValidation) {
        return agentValidation.error;
      }

      const parsedBody = await parseJsonBody(req);
      if ("error" in parsedBody) return parsedBody.error;
      const validation = validateSchema(configUpdateBodySchema, parsedBody.body);
      if ("error" in validation) return validation.error;

      const scopeResult = parseScopeParam(req.nextUrl.searchParams.get("scope"));
      if ("error" in scopeResult) return scopeResult.error;
      const scope = scopeResult.data;

      const existing = await withTelemetrySpan(
        "agent_config.load_existing",
        { attributes: { agentType: agentValidation.data, scope } },
        async () => {
          const { data } = await supabase
            .from("agent_config")
            .select("config")
            .eq("agent_type", agentValidation.data)
            .eq("scope", scope)
            .maybeSingle();
          return data?.config as AgentConfig | undefined;
        }
      );

      const configPayload = buildConfigPayload(
        agentValidation.data,
        scope,
        validation.data,
        existing
      );

      const createdBy = userId;
      const { data, error } = await supabase.rpc("agent_config_upsert", {
        p_agent_type: agentValidation.data,
        p_config: configPayload,
        p_created_by: createdBy,
        p_scope: scope,
        p_summary: validation.data.description ?? undefined,
      });

      if (error) {
        recordTelemetryEvent("agent_config.update_failed", {
          attributes: { agentType: agentValidation.data, scope },
          level: "error",
        });
        return errorResponse({
          err: error,
          error: "internal",
          reason: "Failed to persist configuration",
          status: 500,
        });
      }

      const versionId = Array.isArray(data)
        ? (data[0] as { version_id?: string } | undefined)?.version_id
        : (data as { version_id?: string } | null | undefined)?.version_id;

      if (!versionId) {
        return errorResponse({
          error: "internal",
          reason: "Missing version id from upsert",
          status: 500,
        });
      }

      await bumpTag("configuration");

      emitOperationalAlert("agent_config.updated", {
        attributes: {
          agentType: agentValidation.data,
          scope,
          userId,
          versionId,
        },
        severity: "info",
      });

      return NextResponse.json({ config: configPayload, versionId });
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
        reason: "Failed to update agent configuration",
        status: 500,
      });
    }
  }
);
