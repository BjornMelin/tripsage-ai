"use server";

import {
  type AgentType,
  agentConfigRequestSchema,
  agentTypeSchema,
  configurationAgentConfigSchema,
} from "@schemas/configuration";
import { z } from "zod";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { nowIso, secureId } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { toAbsoluteUrl } from "@/lib/url/server-origin";

const DEFAULT_SCOPE = "global";
const DEFAULT_MODEL = "gpt-4o";

const isE2eBypassEnabled = () =>
  process.env.E2E_BYPASS_RATE_LIMIT === "1" && process.env.NODE_ENV !== "production";

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
      const fallbackConfig = configurationAgentConfigSchema.parse({
        agentType,
        createdAt: now,
        id: `v${Math.floor(Date.now() / 1000)}_${secureId(8)}`,
        model: DEFAULT_MODEL,
        parameters: {
          model: DEFAULT_MODEL,
        },
        scope: DEFAULT_SCOPE,
        updatedAt: now,
      });

      return ok({
        config: fallbackConfig,
        metrics: { lastUpdatedAt: null, versionCount: 0 },
        versions: [],
      });
    }
    return err({
      error: "internal",
      reason: error instanceof Error ? error.message : "Failed to load agent config",
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
    return err({
      error: "internal",
      reason: error instanceof Error ? error.message : "Failed to update configuration",
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
      .looseObject({ error: z.string().optional(), reason: z.string().optional() })
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
    return err({
      error: "internal",
      reason:
        error instanceof Error ? error.message : "Failed to rollback configuration",
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
      .looseObject({ error: z.string().optional(), reason: z.string().optional() })
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
