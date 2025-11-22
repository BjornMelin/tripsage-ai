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
import { z } from "zod";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { withApiGuards } from "@/lib/api/factory";
import { bumpTag } from "@/lib/cache/tags";
import { errorResponse, parseJsonBody, validateSchema } from "@/lib/next/route-helpers";
import { nowIso, secureId } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";

const scopeSchema = z.string().min(1).default("global");
const configUpdateBodySchema = agentConfigRequestSchema.strict();

function ensureAdmin(
  user: unknown
): asserts user is { id: string; user_metadata?: Record<string, unknown> } {
  const candidate = user as { user_metadata?: Record<string, unknown> } | null;
  const isAdmin = Boolean(
    candidate?.user_metadata && candidate.user_metadata.is_admin === true
  );
  if (!isAdmin) {
    throw Object.assign(new Error("forbidden"), { status: 403 });
  }
}

function buildConfigPayload(
  agentType: AgentType,
  scope: string,
  body: z.infer<typeof configUpdateBodySchema>,
  existing?: AgentConfig
): AgentConfig {
  const now = nowIso();
  const baseConfigId =
    existing?.id ?? `v${Math.floor(Date.now() / 1000)}_${secureId(8)}`;
  return configurationAgentConfigSchema.parse({
    agentType,
    createdAt: existing?.createdAt ?? now,
    id: baseConfigId,
    model: body.model ?? existing?.model ?? "gpt-4o",
    parameters: {
      description: body.description ?? existing?.parameters.description,
      maxTokens: body.maxTokens ?? existing?.parameters.maxTokens,
      model: body.model ?? existing?.parameters.model,
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
  telemetry: "config.agents.get",
})(async (req: NextRequest, { user, supabase }, _data, routeContext) => {
  try {
    ensureAdmin(user);
    const { agentType } = await routeContext.params;
    const parsedAgent = agentTypeSchema.safeParse(agentType);
    if (!parsedAgent.success) {
      return errorResponse({
        error: "invalid_request",
        reason: "Invalid agent type",
        status: 400,
      });
    }
    const scope = scopeSchema.parse(req.nextUrl.searchParams.get("scope") ?? undefined);
    const result = await resolveAgentConfig(parsedAgent.data, { scope, supabase });
    return NextResponse.json(result);
  } catch (err) {
    if ((err as { status?: number }).status === 404) {
      return NextResponse.json({ error: "not_found" }, { status: 404 });
    }
    if ((err as { status?: number }).status === 403) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    return errorResponse({
      err,
      error: "internal",
      reason: "Failed to load agent configuration",
      status: 500,
    });
  }
});

export const PUT = withApiGuards({
  auth: true,
  rateLimit: "config:agents:update",
  telemetry: "config.agents.update",
})(async (req: NextRequest, { user }, _data, routeContext) => {
  try {
    ensureAdmin(user);
    const { agentType } = await routeContext.params;
    const parsedAgent = agentTypeSchema.safeParse(agentType);
    if (!parsedAgent.success) {
      return errorResponse({
        error: "invalid_request",
        reason: "Invalid agent type",
        status: 400,
      });
    }

    const parsedBody = await parseJsonBody(req);
    if ("error" in parsedBody) return parsedBody.error;
    const validation = validateSchema(configUpdateBodySchema, parsedBody.body);
    if ("error" in validation) return validation.error;

    const scope = scopeSchema.parse(req.nextUrl.searchParams.get("scope") ?? undefined);
    const supabase = await createServerSupabase();

    const existing = await withTelemetrySpan(
      "agent_config.load_existing",
      { attributes: { agentType: parsedAgent.data, scope } },
      async () => {
        const { data } = await supabase
          .from("agent_config")
          .select("config")
          .eq("agent_type", parsedAgent.data)
          .eq("scope", scope)
          .maybeSingle();
        return data?.config as AgentConfig | undefined;
      }
    );

    const configPayload = buildConfigPayload(
      parsedAgent.data,
      scope,
      validation.data,
      existing
    );

    const createdBy = (user as { id: string } | null)?.id ?? "system";
    const { data, error } = await supabase.rpc("agent_config_upsert", {
      p_agent_type: parsedAgent.data,
      p_config: configPayload,
      p_created_by: createdBy,
      p_scope: scope,
      p_summary: validation.data.description ?? undefined,
    });

    if (error) {
      recordTelemetryEvent("agent_config.update_failed", {
        attributes: { agentType: parsedAgent.data, scope },
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
        agentType: parsedAgent.data,
        scope,
        userId: (user as { id: string } | null)?.id ?? "unknown",
        versionId,
      },
      severity: "info",
    });

    return NextResponse.json({ config: configPayload, versionId });
  } catch (err) {
    if ((err as { status?: number }).status === 403) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    return errorResponse({
      err,
      error: "internal",
      reason: "Failed to update agent configuration",
      status: 500,
    });
  }
});
