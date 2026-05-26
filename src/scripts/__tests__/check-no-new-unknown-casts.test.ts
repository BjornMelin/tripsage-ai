/** @vitest-environment node */

import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-no-new-unknown-casts.mjs");

type RepoFixture = {
  after?: Record<string, string>;
  before: Record<string, string>;
};

function writeFiles(root: string, files: Record<string, string>) {
  for (const [filePath, contents] of Object.entries(files)) {
    const absolutePath = join(root, filePath);
    mkdirSync(dirname(absolutePath), { recursive: true });
    writeFileSync(absolutePath, contents);
  }
}

function runScannerInTempRepo({ after = {}, before }: RepoFixture) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-new-unknown-cast-scan-"));

  try {
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
    execFileSync("git", ["add", "."], { cwd: tempDir, stdio: "ignore" });
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

describe("check-no-new-unknown-casts", () => {
  it("detects newly added unsafe unknown casts in production src files", () => {
    const result = runScannerInTempRepo({
      after: {
        "src/lib/example.ts": `
          export function coerce(value: unknown) {
            return value as unknown as { id: string };
          }
        `,
      },
      before: {
        "src/lib/example.ts": "export const ok = 1;\n",
      },
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("Found new 'as unknown as' casts");
    expect(result.stderr).toContain("src/lib/example.ts");
    expect(result.stderr).toContain("as unknown as");
  });

  it("allows existing baseline casts when the branch does not add new ones", () => {
    const result = runScannerInTempRepo({
      after: {
        "src/lib/example.ts": `
          export const existing = value as unknown as { id: string };
          export const newValue = 1;
        `,
      },
      before: {
        "src/lib/example.ts": `
          export const existing = value as unknown as { id: string };
        `,
      },
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no new 'as unknown as' casts detected");
  });

  it("ignores excluded files, comments, and explicit inline allowlist markers", () => {
    const result = runScannerInTempRepo({
      after: {
        "src/lib/__mocks__/fixture.ts": `
          export const mocked = value as unknown as { id: string };
        `,
        "src/lib/example.test.ts": `
          export const tested = value as unknown as { id: string };
        `,
        "src/lib/example.ts": `
          // value as unknown as { id: string }
          export const justified = value as unknown as { id: string }; // cast-ok: fixture documents an intentional legacy exception
        `,
      },
      before: {
        "src/lib/example.ts": "export const ok = 1;\n",
      },
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no new 'as unknown as' casts detected");
  });
});
