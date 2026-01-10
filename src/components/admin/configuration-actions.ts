"use server";

import {
  type AgentType,
  agentConfigRequestSchema,
  agentTypeSchema,
  configurationAgentConfigSchema,
} from "@schemas/configuration";
import { z } from "zod";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { isE2eBypassEnabled } from "@/lib/config/helpers";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { nowIso, secureId } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { toAbsoluteUrl } from "@/lib/url/server-origin";

const DEFAULT_SCOPE = "global";
const DEFAULT_MODEL = "gpt-4o";

const configurationActionsLogger = createServerLogger("admin.configuration");

export type AgentVersion = {
  id: string;
  createdAt: string;
  createdBy: string | null;
  summary: string | null;
};

export type AgentMetrics = {
  versionCount: number;
  lastUpdatedAt: string | null;
};

export type AgentBundle = {
  config: Awaited<ReturnType<typeof resolveAgentConfig>>["config"];
  metrics: AgentMetrics;
  versions: AgentVersion[];
};

export type AgentConfigMutationResponse = {
  config: Awaited<ReturnType<typeof resolveAgentConfig>>["config"];
  versionId: string;
};

export async function fetchAgentBundle(
  agentTypeRaw: string
): Promise<Result<AgentBundle, ResultError>> {
  const parsed = agentTypeSchema.safeParse(agentTypeRaw);
  if (!parsed.success) {
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(parsed.error),
      issues: parsed.error.issues,
      reason: "Invalid agent type",
    });
  }
  const agentType = parsed.data;

  let config: Awaited<ReturnType<typeof resolveAgentConfig>>;
  try {
    config = await resolveAgentConfig(agentType, { scope: DEFAULT_SCOPE });
  } catch (error) {
    if (isE2eBypassEnabled()) {
      const now = nowIso();
      const timestamp = now.replace(/[-:T.Z]/g, "").slice(0, 14);

      // Construct a fallback config that satisfies schema constraints.
      // `versionIdSchema` and `agentConfigRequestSchema` expect:
      // - `id`: `v${timestamp}_${secureId(8)}` (matches /^v\d+_[a-f0-9]{8}$/)
      // - `model`: `DEFAULT_MODEL` ("gpt-4o") which is currently allowed.
      // Validation failure is treated as an error on purpose to surface schema changes
      // early in tests instead of silently returning a mismatched fallback.
      const fallbackConfigParsed = configurationAgentConfigSchema.safeParse({
        agentType,
        createdAt: now,
        id: `v${timestamp}_${secureId(8)}`,
        model: DEFAULT_MODEL,
        parameters: {
          model: DEFAULT_MODEL,
        },
        scope: DEFAULT_SCOPE,
        updatedAt: now,
      });

      if (!fallbackConfigParsed.success) {
        // Intentionally return an error to surface schema mismatches during tests.
        return err({
          error: "internal",
          reason: "Failed to construct fallback config",
        });
      }

      return ok({
        config: fallbackConfigParsed.data,
        metrics: { lastUpdatedAt: null, versionCount: 0 },
        versions: [],
      });
    }

    configurationActionsLogger.error("agent_bundle_load_failed", {
      agentType,
      error:
        error instanceof Error
          ? error.message.slice(0, 500)
          : String(error).slice(0, 500),
      errorName: error instanceof Error ? error.name : "unknown_error",
      errorStack: error instanceof Error ? error.stack?.slice(0, 500) : undefined,
    });

    return err({
      error: "internal",
      reason: "Internal server error",
    });
  }

  const supabase = await createServerSupabase();
  const { data: versions, error: versionsError } = await supabase
    .from("agent_config_versions")
    .select("id, created_at, created_by, summary")
    .eq("agent_type", agentType)
    .eq("scope", DEFAULT_SCOPE)
    .order("created_at", { ascending: false })
    .limit(20);

  if (versionsError) {
    return err({
      error: "internal",
      reason: "Failed to load agent config versions",
    });
  }

  const metrics: AgentMetrics = {
    lastUpdatedAt: versions?.[0]?.created_at ?? null,
    versionCount: versions?.length ?? 0,
  };

  return ok({
    config: config.config,
    metrics,
    versions: (versions ?? []).map(
      (v) =>
        ({
          createdAt: v.created_at,
          createdBy: v.created_by,
          id: v.id,
          summary: v.summary,
        }) satisfies AgentVersion
    ),
  });
}

export async function updateAgentConfigAction(
  agentType: AgentType,
  payload: Record<string, unknown>
): Promise<Result<AgentConfigMutationResponse, ResultError>> {
  // SSRF prevention: validate agentType against allow-list schema
  const parsed = agentTypeSchema.safeParse(agentType);
  if (!parsed.success) {
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(parsed.error),
      issues: parsed.error.issues,
      reason: "Invalid agent type",
    });
  }

  const parsedPayload = agentConfigRequestSchema.safeParse(payload);
  if (!parsedPayload.success) {
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(parsedPayload.error),
      issues: parsedPayload.error.issues,
      reason: "Invalid agent config payload",
    });
  }

  // Use absolute URL with trusted origin to prevent SSRF
  const url = toAbsoluteUrl(`/api/config/agents/${parsed.data}`);
  let res: Response;
  try {
    res = await fetch(url, {
      body: JSON.stringify(parsedPayload.data),
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      method: "PUT",
    });
  } catch (error) {
    configurationActionsLogger.error("agent_config_update_failed", {
      agentType: parsed.data,
      error:
        error instanceof Error
          ? error.message.slice(0, 500)
          : String(error).slice(0, 500),
      errorName: error instanceof Error ? error.name : "unknown_error",
      errorStack: error instanceof Error ? error.stack?.slice(0, 500) : undefined,
    });
    return err({
      error: "internal",
      reason: "Internal server error",
    });
  }
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      // ignore parse errors
    }

    const errorBody = z
      .looseObject({
        error: z.string().optional(),
        reason: z.string().optional(),
      })
      .safeParse(body);

    return err({
      error:
        (errorBody.success ? errorBody.data.error : undefined) ??
        (res.status === 403
          ? "forbidden"
          : res.status === 401
            ? "unauthorized"
            : "internal"),
      reason:
        (errorBody.success ? errorBody.data.reason : undefined) ??
        "Failed to update configuration",
    });
  }

  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return err({
      error: "internal",
      reason: "Invalid JSON response from config update endpoint",
    });
  }
  const parsedResponse = z
    .strictObject({
      config: configurationAgentConfigSchema,
      versionId: z.uuid(),
    })
    .safeParse(body);

  if (!parsedResponse.success) {
    return err({
      error: "internal",
      fieldErrors: zodErrorToFieldErrors(parsedResponse.error),
      issues: parsedResponse.error.issues,
      reason: "Invalid response from config update endpoint",
    });
  }

  return ok(parsedResponse.data);
}

export async function rollbackAgentConfigAction(
  agentType: AgentType,
  versionId: string
): Promise<Result<AgentConfigMutationResponse, ResultError>> {
  // SSRF prevention: validate agentType against allow-list schema
  const parsedAgentType = agentTypeSchema.safeParse(agentType);
  if (!parsedAgentType.success) {
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(parsedAgentType.error),
      issues: parsedAgentType.error.issues,
      reason: "Invalid agent type",
    });
  }

  // SSRF prevention: validate versionId format (route expects UUID)
  const parsedVersionId = z.uuid().safeParse(versionId);
  if (!parsedVersionId.success) {
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(parsedVersionId.error),
      issues: parsedVersionId.error.issues,
      reason: "Invalid version ID format",
    });
  }

  // Use absolute URL with trusted origin to prevent SSRF
  const url = toAbsoluteUrl(
    `/api/config/agents/${parsedAgentType.data}/rollback/${parsedVersionId.data}`
  );
  let res: Response;
  try {
    res = await fetch(url, {
      cache: "no-store",
      method: "POST",
    });
  } catch (error) {
    configurationActionsLogger.error("agent_config_rollback_failed", {
      agentType: parsedAgentType.data,
      error:
        error instanceof Error
          ? error.message.slice(0, 500)
          : String(error).slice(0, 500),
      errorName: error instanceof Error ? error.name : "unknown_error",
      errorStack: error instanceof Error ? error.stack?.slice(0, 500) : undefined,
      versionId: parsedVersionId.data,
    });
    return err({
      error: "internal",
      reason: "Internal server error",
    });
  }
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      // ignore parse errors
    }

    const errorBody = z
      .looseObject({
        error: z.string().optional(),
        reason: z.string().optional(),
      })
      .safeParse(body);

    return err({
      error:
        (errorBody.success ? errorBody.data.error : undefined) ??
        (res.status === 403
          ? "forbidden"
          : res.status === 401
            ? "unauthorized"
            : res.status === 404
              ? "not_found"
              : "internal"),
      reason:
        (errorBody.success ? errorBody.data.reason : undefined) ??
        "Failed to rollback configuration",
    });
  }

  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return err({
      error: "internal",
      reason: "Invalid JSON response from config rollback endpoint",
    });
  }
  const parsedResponse = z
    .strictObject({
      config: configurationAgentConfigSchema,
      versionId: z.uuid(),
    })
    .safeParse(body);

  if (!parsedResponse.success) {
    return err({
      error: "internal",
      fieldErrors: zodErrorToFieldErrors(parsedResponse.error),
      issues: parsedResponse.error.issues,
      reason: "Invalid response from config rollback endpoint",
    });
  }

  return ok(parsedResponse.data);
}
