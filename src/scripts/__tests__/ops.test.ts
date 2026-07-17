/** @vitest-environment node */

import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/ops.ts");
const tsxCliPath = fileURLToPath(import.meta.resolve("tsx/cli"));
const operationalEnvKeys = [
  "AI_GATEWAY_API_KEY",
  "AI_GATEWAY_URL",
  "ANTHROPIC_API_KEY",
  "APP_BASE_URL",
  "BYOK_HEALTHCHECK_KEY",
  "NEXT_PUBLIC_APP_URL",
  "NEXT_PUBLIC_BASE_URL",
  "NEXT_PUBLIC_SITE_URL",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_SUPABASE_URL",
  "OPENAI_API_KEY",
  "OPENROUTER_API_KEY",
  "QSTASH_TOKEN",
  "SUPABASE_SERVICE_ROLE_KEY",
  "UPSTASH_REDIS_REST_TOKEN",
  "UPSTASH_REDIS_REST_URL",
  "XAI_API_KEY",
] as const;

function runOps(args: string[] = []) {
  const env = { ...process.env, FORCE_COLOR: "0" };
  for (const key of operationalEnvKeys) {
    Reflect.deleteProperty(env, key);
  }

  return spawnSync(process.execPath, [tsxCliPath, scriptPath, ...args], {
    encoding: "utf8",
    env,
    timeout: 10_000,
  });
}

describe("ops CLI help", () => {
  it.each([["--help"], ["-h"]])("prints help for %s", (flag) => {
    const result = runOps([flag]);

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("Infrastructure checks:");
    expect(result.stderr).toBe("");
  });

  it("prints help when no command is provided", () => {
    const result = runOps();

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("Test analysis:");
    expect(result.stderr).toBe("");
  });

  it.each([
    ["infra", "check", "supabase", "--help"],
    ["--help", "infra", "check", "supabase"],
  ])("does not dispatch a command when help is requested", (...args) => {
    const result = runOps(args);

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("pnpm ops infra check supabase");
    expect(result.stderr).toBe("");
  });

  it("rejects an unknown non-empty command", () => {
    const result = runOps(["unknown"]);

    expect(result.status).toBe(1);
    expect(result.stdout).toContain("Infrastructure checks:");
    expect(result.stderr).toContain('Error: Unknown command "unknown"');
  });
});
