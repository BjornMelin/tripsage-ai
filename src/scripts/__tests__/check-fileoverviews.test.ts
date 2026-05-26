/** @vitest-environment node */

import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-fileoverviews.mjs");

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
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-fileoverview-full-scan-"));

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
  after: Record<string, string>,
  deletedFiles: string[] = []
) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-fileoverview-diff-scan-"));

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

    for (const filePath of deletedFiles) {
      unlinkSync(join(tempDir, filePath));
    }
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

describe("check-fileoverviews", () => {
  it("detects multi-line @fileoverview blocks in production source files", () => {
    const result = runFullScannerInTempRepo({
      "src/lib/example.ts": `
        /**
         * @fileoverview Describes the module.
         *
         * Extra implementation detail belongs in docs.
         */
        export const example = true;
      `,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("src/lib/example.ts");
    expect(result.stderr).toContain("Multi-line @fileoverview block detected");
  });

  it("allows one-line descriptions, documented exceptions, tests, and mocks", () => {
    const result = runFullScannerInTempRepo({
      "src/lib/__mocks__/fixture.ts": `
        /**
         * @fileoverview Mock-only module.
         *
         * Mocks are excluded from this production-code guard.
         */
        export const mockOnly = true;
      `,
      "src/lib/example.test.ts": `
        /**
         * @fileoverview Test-only module.
         *
         * Tests are excluded from this production-code guard.
         */
        export const testOnly = true;
      `,
      "src/lib/example.ts": `
        /**
         * @fileoverview Describes the module.
         */
        export const example = true;
      `,
      "src/lib/legacy.ts": `
        /**
         * @fileoverview fileoverview-ok: generated compatibility wrapper.
         *
         * Extra generated detail is preserved here.
         */
        export const legacy = true;
      `,
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no @fileoverview drift detected");
  });

  it("rejects @fileoverview blocks without descriptions", () => {
    const result = runFullScannerInTempRepo({
      "src/lib/example.ts": `
        /**
         * @fileoverview
         */
        export const example = true;
      `,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("@fileoverview must include a short description");
  });

  it("checks committed branch diffs and skips deleted files", () => {
    const result = runDiffScannerInTempRepo(
      {
        "src/lib/deleted.ts": `
          /**
           * @fileoverview Deleted module.
           *
           * Existing drift should not matter after deletion.
           */
          export const deleted = true;
        `,
        "src/lib/unchanged.ts": `
          /**
           * @fileoverview Existing unchanged drift.
           *
           * Diff mode should not scan unchanged files.
           */
          export const unchanged = true;
        `,
      },
      {
        "src/lib/changed.ts": `
          /**
           * @fileoverview Changed module.
           *
           * New drift should be reported.
           */
          export const changed = true;
        `,
      },
      ["src/lib/deleted.ts"]
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("src/lib/changed.ts");
    expect(result.stderr).not.toContain("src/lib/deleted.ts");
    expect(result.stderr).not.toContain("src/lib/unchanged.ts");
  });
});
