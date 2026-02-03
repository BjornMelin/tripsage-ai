/**
 * @fileoverview Agent configuration resolver backed by Supabase with Upstash cache. Fetches configuration for a given agent type and scope, validates via Zod, and caches the result with cache-tag versioning for fast reuse across agents.
 */

import "server-only";

import type { AgentConfig, AgentType } from "@schemas/configuration";
import { configurationAgentConfigSchema } from "@schemas/configuration";
import { cacheLife, cacheTag } from "next/cache";
import { versionedKey } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { getMaybeSingle } from "@/lib/supabase/typed-helpers";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";

const CACHE_TAG = "configuration";
const CACHE_TTL_SECONDS = 15 * 60; // 15 minutes
const CACHE_PROFILE: string = "agentConfiguration";

/**
 * Resolved agent configuration.
 * @param config - The agent configuration.
 * @param versionId - The version ID of the agent configuration.
 */
export type ResolvedAgentConfig = {
  config: AgentConfig;
  versionId: string;
};

/**
 * Resolve agent configuration options.
 * @param scope - The scope of the agent configuration.
 * @param cacheTtlSeconds - The cache TTL in seconds.
 */
export type ResolveAgentConfigOptions = {
  scope?: string;
  cacheTtlSeconds?: number;
};

/**
 * Resolve an agent configuration with cache + Supabase fallback.
 *
 * @param agentType Canonical agent type identifier.
 * @param options Optional resolver overrides.
 * @returns Parsed configuration and active version id.
 * @see docs/architecture/decisions/adr-0052-agent-configuration-backend.md
 */
export async function resolveAgentConfig(
  agentType: AgentType,
  options: ResolveAgentConfigOptions = {}
): Promise<ResolvedAgentConfig> {
  "use cache";

  const scope = options.scope ?? "global";
  const cacheTtl = options.cacheTtlSeconds ?? CACHE_TTL_SECONDS;
  const usesDefaultTtl = options.cacheTtlSeconds === undefined;

  try {
    cacheTag(
      CACHE_TAG,
      `${CACHE_TAG}:${agentType}`,
      `${CACHE_TAG}:${agentType}:${scope}`
    );
    if (usesDefaultTtl) {
      cacheLife(CACHE_PROFILE);
    } else {
      cacheLife({
        expire: Math.max(cacheTtl * 4, cacheTtl + 60),
        revalidate: cacheTtl,
        stale: 60,
      });
    }
  } catch {
    // Ignore Cache Components directives when executed outside the Next runtime (e.g. unit tests).
  }

  return await withTelemetrySpan(
    "agent_config.resolve",
    {
      attributes: { agentType, scope },
    },
    async () => {
      const cacheKey = await versionedKey(CACHE_TAG, `agent:${agentType}:${scope}`);
      const cached = await getCachedJson<ResolvedAgentConfig>(cacheKey);
      if (cached) {
        return cached;
      }

      // Use admin client to bypass RLS for agent config lookup
      // Agent configs are protected by RLS and require admin privileges
      const supabase = createAdminSupabase();
      const { data, error } = await getMaybeSingle(
        supabase,
        "agent_config",
        (qb) => qb.eq("agent_type", agentType).eq("scope", scope),
        { select: "config, version_id", validate: false }
      );

      if (error) {
        emitOperationalAlertOncePerWindow({
          attributes: { agentType, reason: "db_error", scope },
          event: "agent_config.resolve_failed",
          windowMs: 60 * 60 * 1000, // 1h
        });
        throw error;
      }
      if (!data) {
        emitOperationalAlertOncePerWindow({
          attributes: { agentType, reason: "not_found", scope },
          event: "agent_config.resolve_failed",
          windowMs: 60 * 60 * 1000, // 1h
        });
        throw Object.assign(new Error("Agent configuration not found"), {
          status: 404,
        });
      }

      const parsed = configurationAgentConfigSchema.safeParse(data.config);
      if (!parsed.success) {
        emitOperationalAlertOncePerWindow({
          attributes: { agentType, reason: "schema_invalid", scope },
          event: "agent_config.resolve_failed",
          windowMs: 60 * 60 * 1000, // 1h
        });
        recordTelemetryEvent("agent_config.schema_invalid", {
          attributes: {
            agentType,
            issues: parsed.error.issues.length,
            scope,
          },
          level: "error",
        });
        throw parsed.error;
      }

      const resolved = {
        config: parsed.data,
        versionId: data.version_id,
      } satisfies ResolvedAgentConfig;

      await setCachedJson(cacheKey, resolved, cacheTtl);
      return resolved;
    }
  );
}
