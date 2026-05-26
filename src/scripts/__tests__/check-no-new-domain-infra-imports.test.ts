/** @vitest-environment node */

import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-no-new-domain-infra-imports.mjs");

function writeFiles(root: string, files: Record<string, string>) {
  for (const [filePath, contents] of Object.entries(files)) {
    const absolutePath = join(root, filePath);
    mkdirSync(dirname(absolutePath), { recursive: true });
    writeFileSync(absolutePath, contents);
  }
}

function initRepo(tempDir: string) {
  execFileSync("git", ["init", "--initial-branch=main"], {
    cwd: tempDir,
    stdio: "ignore",
  });
  execFileSync("git", ["config", "user.email", "test@example.com"], {
    cwd: tempDir,
    stdio: "ignore",
  });
  execFileSync("git", ["config", "user.name", "TripSage Test"], {
    cwd: tempDir,
    stdio: "ignore",
  });
}

function runGuardInTempRepo(
  before: Record<string, string>,
  after: Record<string, string>
) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-domain-infra-guard-"));

  try {
    initRepo(tempDir);
    writeFiles(tempDir, before);
    execFileSync("git", ["add", "."], { cwd: tempDir, stdio: "ignore" });
    execFileSync("git", ["commit", "-m", "baseline"], {
      cwd: tempDir,
      stdio: "ignore",
    });
    execFileSync("git", ["checkout", "-b", "feature"], {
      cwd: tempDir,
      stdio: "ignore",
    });

    writeFiles(tempDir, after);
    execFileSync("git", ["add", "-A"], { cwd: tempDir, stdio: "ignore" });
    execFileSync("git", ["commit", "-m", "feature"], {
      cwd: tempDir,
      stdio: "ignore",
    });

    return spawnSync(process.execPath, [scriptPath], {
      cwd: tempDir,
      encoding: "utf8",
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

describe("check-no-new-domain-infra-imports", () => {
  it("detects newly added domain imports from lib infrastructure", () => {
    const result = runGuardInTempRepo(
      {
        "src/domain/trips/service.ts": "export const existing = true;\n",
      },
      {
        "src/domain/trips/service.ts": `
          import { createServerSupabase } from "@/lib/supabase/server";

          export const existing = true;
        `,
      }
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("Found new Domain");
    expect(result.stderr).toContain("src/domain/trips/service.ts");
    expect(result.stderr).toContain("@/lib/supabase/server");
  });

  it("detects export and dynamic import forms", () => {
    const result = runGuardInTempRepo(
      {
        "src/domain/activities/service.ts": "export const existing = true;\n",
      },
      {
        "src/domain/activities/service.ts": `
          export { createServerLogger } from "@/lib/telemetry/logger";

          export async function loadLimiter() {
            return import("@/lib/ratelimit/server");
          }
        `,
      }
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("@/lib/telemetry/logger");
    expect(result.stderr).toContain("@/lib/ratelimit/server");
  });

  it("allows legacy baseline imports when no new infra import is added", () => {
    const result = runGuardInTempRepo(
      {
        "src/domain/flights/service.ts": `
          import { redis } from "@/lib/redis";

          export const existing = true;
        `,
      },
      {
        "src/domain/flights/service.ts": `
          import { redis } from "@/lib/redis";

          export const existing = true;
          export const changed = true;
        `,
      }
    );

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no new Domain");
  });

  it("ignores excluded files, comments, string literals, and allowlisted imports", () => {
    const result = runGuardInTempRepo(
      {
        "src/domain/profile/service.ts": "export const existing = true;\n",
      },
      {
        "src/domain/profile/__mocks__/fixture.ts": `
          import { redis } from "@/lib/redis";
          export const mockOnly = true;
        `,
        "src/domain/profile/__tests__/service.test.ts": `
          import { createServerSupabase } from "@/lib/supabase/server";
          export const testOnly = true;
        `,
        "src/domain/profile/service.ts": `
          // import { redis } from "@/lib/redis";
          const text = "import('@/lib/qstash/client')";
          import { logger } from "@/lib/telemetry/logger"; // domain-infra-ok: migration seam under active refactor

          export const existing = true;
          export const changed = text.length + String(logger).length;
        `,
      }
    );

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no new Domain");
  });
});
