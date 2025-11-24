"use server";

import { type AgentType, agentTypeSchema } from "@schemas/configuration";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createServerSupabase } from "@/lib/supabase/server";
import { toAbsoluteUrl } from "@/lib/url/server-origin";

const DEFAULT_SCOPE = "global";

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

export async function fetchAgentBundle(agentTypeRaw: string) {
  const parsed = agentTypeSchema.safeParse(agentTypeRaw);
  if (!parsed.success) throw new Error("invalid agent type");
  const agentType = parsed.data;

  const config = await resolveAgentConfig(agentType, { scope: DEFAULT_SCOPE });

  const supabase = await createServerSupabase();
  const { data: versions } = await supabase
    .from("agent_config_versions")
    .select("id, created_at, created_by, summary")
    .eq("agent_type", agentType)
    .eq("scope", DEFAULT_SCOPE)
    .order("created_at", { ascending: false })
    .limit(20);

  const metrics: AgentMetrics = {
    lastUpdatedAt: versions?.[0]?.created_at ?? null,
    versionCount: versions?.length ?? 0,
  };

  return {
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
  } as const;
}

export async function updateAgentConfigAction(
  agentType: AgentType,
  payload: Record<string, unknown>
) {
  // Use absolute URL with trusted origin to prevent SSRF
  const url = toAbsoluteUrl(`/api/config/agents/${agentType}`);
  const res = await fetch(url, {
    body: JSON.stringify(payload),
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    method: "PUT",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.reason ?? "Failed to update configuration");
  }
  return (await res.json()) as { config: unknown; versionId: string };
}

export async function rollbackAgentConfigAction(
  agentType: AgentType,
  versionId: string
) {
  // Use absolute URL with trusted origin to prevent SSRF
  const url = toAbsoluteUrl(`/api/config/agents/${agentType}/rollback/${versionId}`);
  const res = await fetch(url, {
    cache: "no-store",
    method: "POST",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.reason ?? "Failed to rollback configuration");
  }
  return (await res.json()) as { config: unknown; versionId: string };
}
