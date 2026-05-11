/** @vitest-environment node */

import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-no-secrets.mjs");

function runScannerInTempRepo(contents: string, fileName = "fixture.ts") {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-secret-scan-"));

  try {
    execFileSync("git", ["init"], { cwd: tempDir, stdio: "ignore" });
    writeFileSync(join(tempDir, fileName), contents);
    execFileSync("git", ["add", fileName], { cwd: tempDir, stdio: "ignore" });

    return spawnSync(process.execPath, [scriptPath, "--full"], {
      cwd: tempDir,
      encoding: "utf8",
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

describe("check-no-secrets", () => {
  it("detects sensitive provider env assignments from the runtime schema", () => {
    const databaseUrlName = ["DATABASE", "URL"].join("_");
    const openRouterName = ["OPENROUTER", "API", "KEY"].join("_");
    const byokHealthName = ["BYOK", "HEALTHCHECK", "KEY"].join("_");
    const openRouterKey = `sk-or-v1-${"a".repeat(48)}`;
    const byokHealthKey = "byok-health-live-secret-1234567890abcdef";

    const result = runScannerInTempRepo(`
      export const env = {
        ${databaseUrlName}: "postgresql://user:live-supersecretpassword@db.internal/app",
        ${openRouterName}: "${openRouterKey}",
        ${byokHealthName}: "${byokHealthKey}",
      };
    `);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(databaseUrlName);
    expect(result.stderr).toContain(openRouterName);
    expect(result.stderr).toContain(byokHealthName);
    expect(result.stderr).not.toContain("supersecretpassword");
    expect(result.stderr).not.toContain(openRouterKey);
    expect(result.stderr).not.toContain(byokHealthKey);
  });

  it("detects vendor-specific key shapes outside env assignment syntax", () => {
    const anthropicKey = `sk-ant-${"A".repeat(36)}`;

    const result = runScannerInTempRepo(`
      export const badFixture = "${anthropicKey}";
    `);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("anthropic_api_key");
    expect(result.stderr).not.toContain(anthropicKey);
  });

  it("scans SQL migrations for token-shaped secrets", () => {
    const anthropicKey = `sk-ant-${"B".repeat(36)}`;

    const result = runScannerInTempRepo(
      `
        -- fixture migration
        select '${anthropicKey}';
      `,
      "fixture.sql"
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("anthropic_api_key");
    expect(result.stderr).not.toContain(anthropicKey);
  });

  it("detects unquoted env-template secret assignments", () => {
    const databaseUrlName = ["DATABASE", "URL"].join("_");
    const result = runScannerInTempRepo(
      `${databaseUrlName}=postgresql://user:live-supersecretpassword@db.internal/app\n`,
      ".env.example"
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(databaseUrlName);
    expect(result.stderr).not.toContain("supersecretpassword");
  });

  it("allows placeholders for expanded sensitive env names", () => {
    const result = runScannerInTempRepo(`
      export const env = {
        FIRECRAWL_API_KEY: "placeholder-firecrawl-api-key",
        HMAC_SECRET: "changeme-hmac-secret-placeholder",
      };
    `);

    expect(result.status).toBe(0);
  });
});
