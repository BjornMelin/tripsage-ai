#!/usr/bin/env tsx

/**
 * @fileoverview Consolidated ops CLI for infra and AI config readiness checks.
 *
 * Subcommands (run from frontend/):
 *   pnpm ops infra check supabase   -- Supabase auth health (+ storage with service role key)
 *   pnpm ops infra check upstash    -- Upstash Redis ping + QStash token probe
 *   pnpm ops ai check config        -- AI Gateway/BYOK credential presence + gateway reachability
 *   pnpm ops check all              -- Run all checks with summary
 *
 * BYOK providers checked: OpenAI, OpenRouter, Anthropic, xAI
 */

import process from "node:process";
import { createClient } from "@supabase/supabase-js";
import { Redis } from "@upstash/redis";
import { z } from "zod";

type Command = () => Promise<void>;

const supabaseEnvSchema = z.object({
  supabaseAnonKey: z.string().min(1),
  supabaseServiceRoleKey: z.string().optional(),
  supabaseUrl: z.string().url(),
});

const upstashEnvSchema = z.object({
  redisToken: z.string().min(1),
  redisUrl: z.string().url(),
});

const qstashEnvSchema = z.object({
  qstashToken: z.string().min(1),
});

const aiEnvSchema = z.object({
  aiGatewayApiKey: z.string().min(1).optional(),
  aiGatewayUrl: z.string().url().optional(),
  anthropicApiKey: z.string().min(1).optional(),
  openaiApiKey: z.string().min(1).optional(),
  openrouterApiKey: z.string().min(1).optional(),
  xaiApiKey: z.string().min(1).optional(),
});

function formatError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function printUsage(): void {
  console.log("Usage:");
  console.log("  pnpm ops infra check supabase   -- Supabase auth health + storage");
  console.log("  pnpm ops infra check upstash    -- Redis ping + QStash probe");
  console.log("  pnpm ops ai check config        -- AI Gateway/BYOK credentials");
  console.log("  pnpm ops check all              -- Run all checks");
}

async function checkSupabase(): Promise<void> {
  const env = supabaseEnvSchema.parse({
    supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    supabaseServiceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY,
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
  });

  const healthRes = await fetch(`${env.supabaseUrl}/auth/v1/health`, {
    headers: {
      apikey: env.supabaseAnonKey,
    },
    method: "GET",
  });

  if (!healthRes.ok) {
    throw new Error(
      `Supabase auth health failed (${healthRes.status} ${healthRes.statusText})`
    );
  }

  if (env.supabaseServiceRoleKey) {
    const client = createClient(env.supabaseUrl, env.supabaseServiceRoleKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    const { error } = await client.storage.listBuckets();
    if (error) {
      throw new Error(`Supabase storage list failed: ${error.message}`);
    }
  }

  console.log("Supabase check: OK");
}

async function checkUpstash(): Promise<void> {
  const redisEnv = upstashEnvSchema.parse({
    redisToken: process.env.UPSTASH_REDIS_REST_TOKEN,
    redisUrl: process.env.UPSTASH_REDIS_REST_URL,
  });

  const redis = new Redis({
    token: redisEnv.redisToken,
    url: redisEnv.redisUrl,
  });

  const ping = await redis.ping();
  if (ping !== "PONG") {
    throw new Error(`Upstash Redis ping failed (got ${ping})`);
  }

  const qstashEnv = qstashEnvSchema.safeParse({
    qstashToken: process.env.QSTASH_TOKEN,
  });

  if (qstashEnv.success) {
    const topicsRes = await fetch("https://qstash.upstash.io/v2/topics", {
      headers: {
        /* biome-ignore lint/style/useNamingConvention: HTTP header key */
        Authorization: `Bearer ${qstashEnv.data.qstashToken}`,
      },
      method: "GET",
    });

    if (!topicsRes.ok) {
      throw new Error(
        `QStash topics endpoint failed (${topicsRes.status} ${topicsRes.statusText})`
      );
    }
  }

  console.log("Upstash check: OK");
}

async function checkAiConfig(): Promise<void> {
  const env = aiEnvSchema.parse({
    aiGatewayApiKey: process.env.AI_GATEWAY_API_KEY,
    aiGatewayUrl: process.env.AI_GATEWAY_URL,
    anthropicApiKey: process.env.ANTHROPIC_API_KEY,
    openaiApiKey: process.env.OPENAI_API_KEY,
    openrouterApiKey: process.env.OPENROUTER_API_KEY,
    xaiApiKey: process.env.XAI_API_KEY,
  });

  const hasProviderKey =
    env.openaiApiKey ||
    env.openrouterApiKey ||
    env.anthropicApiKey ||
    env.xaiApiKey;

  if (!env.aiGatewayApiKey && !hasProviderKey) {
    throw new Error("No AI credentials found (gateway or provider keys)");
  }

  // Show which credentials are configured
  const configured: string[] = [];
  if (env.aiGatewayApiKey) configured.push("AI Gateway");
  if (env.openaiApiKey) configured.push("OpenAI");
  if (env.openrouterApiKey) configured.push("OpenRouter");
  if (env.anthropicApiKey) configured.push("Anthropic");
  if (env.xaiApiKey) configured.push("xAI");
  console.log(`  Configured: ${configured.join(", ")}`);

  if (env.aiGatewayApiKey && env.aiGatewayUrl) {
    const res = await fetch(env.aiGatewayUrl, {
      headers: {
        /* biome-ignore lint/style/useNamingConvention: HTTP header key */
        Authorization: `Bearer ${env.aiGatewayApiKey}`,
      },
      method: "HEAD",
    });

    if (!res.ok) {
      throw new Error(
        `AI Gateway unreachable (${res.status} ${res.statusText}); check AI_GATEWAY_URL/API_KEY`
      );
    }
  }

  console.log("AI config check: OK");
}

async function checkAll(): Promise<void> {
  const checks = [
    { fn: checkSupabase, name: "Supabase" },
    { fn: checkUpstash, name: "Upstash" },
    { fn: checkAiConfig, name: "AI Config" },
  ];

  const results: Array<{ name: string; ok: boolean; error?: string }> = [];

  for (const { name, fn } of checks) {
    console.log(`\n[${name}]`);
    try {
      await fn();
      results.push({ name, ok: true });
    } catch (error) {
      results.push({ error: formatError(error), name, ok: false });
      console.error(`  Error: ${formatError(error)}`);
    }
  }

  console.log("\n" + "=".repeat(40));
  console.log("Summary:");
  for (const r of results) {
    console.log(`  ${r.ok ? "✅" : "❌"} ${r.name}`);
  }
  console.log("=".repeat(40));

  const failed = results.filter((r) => !r.ok);
  if (failed.length > 0) {
    throw new Error(`${failed.length} check(s) failed`);
  }
}

const commandMap: Record<string, Command> = {
  "ai:check:config": checkAiConfig,
  "check:all": checkAll,
  "infra:check:supabase": checkSupabase,
  "infra:check:upstash": checkUpstash,
};

async function main(): Promise<void> {
  const [, , ...args] = process.argv;
  const key = args.join(":");

  const command = commandMap[key];
  if (!command) {
    printUsage();
    process.exit(1);
    return;
  }

  try {
    await command();
  } catch (error) {
    console.error(`Error: ${formatError(error)}`);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(`Error: ${formatError(error)}`);
  process.exit(1);
});
