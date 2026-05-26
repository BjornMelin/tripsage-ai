/** @vitest-environment node */

import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-zod-v4-usage.mjs");

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

function runFullScannerInTempRepo(files: Record<string, string>) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-zod-v4-full-scan-"));

  try {
    initRepo(tempDir);
    writeFiles(tempDir, files);
    execFileSync("git", ["add", "."], { cwd: tempDir, stdio: "ignore" });

    return spawnSync(process.execPath, [scriptPath, "--full"], {
      cwd: tempDir,
      encoding: "utf8",
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

function runDiffScannerInTempRepo(
  before: Record<string, string>,
  after: Record<string, string>
) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-zod-v4-diff-scan-"));

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

describe("check-zod-v4-usage", () => {
  it("detects deprecated Zod string helper method chains in production files", () => {
    const result = runFullScannerInTempRepo({
      "src/domain/schemas/example.ts": `
        import { z } from "zod";

        export const Example = z.object({
          email: z.string().email(),
          id: z.string().uuid(),
          homepage: z.string().url(),
          createdAt: z.string().datetime(),
        });
      `,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("zod-string-email");
    expect(result.stderr).toContain("zod-string-uuid");
    expect(result.stderr).toContain("zod-string-url");
    expect(result.stderr).toContain("zod-string-datetime");
  });

  it("allows Zod v4 top-level helpers and documented exceptions", () => {
    const result = runFullScannerInTempRepo({
      "src/domain/schemas/__mocks__/fixture.ts": `
        export const mocked = z.string().email();
      `,
      "src/domain/schemas/example.test.ts": `
        export const tested = z.string().email();
      `,
      "src/domain/schemas/example.ts": `
        import { z } from "zod";

        // z.string().email()
        /*
         * z.string().uuid()
         */
        export const Example = z.object({
          email: z.email(),
          id: z.uuid(),
          homepage: z.url(),
          createdAt: z.iso.datetime(),
          legacy: z.string().email(), // zod-v4-ok: legacy provider demands method-chain schema metadata
        });
      `,
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no Zod v4 style violations detected");
  });

  it("checks committed branch diffs and ignores deleted files", () => {
    const result = runDiffScannerInTempRepo(
      {
        "src/domain/schemas/deleted.ts": `
          import { z } from "zod";
          export const Deleted = z.string().email();
        `,
        "src/domain/schemas/example.ts": `
          import { z } from "zod";
          export const Example = z.email();
        `,
      },
      {
        "src/domain/schemas/example.ts": `
          import { z } from "zod";
          export const Example = z.string().email();
        `,
      }
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("src/domain/schemas/example.ts");
    expect(result.stderr).not.toContain("src/domain/schemas/deleted.ts");
  });
});
