/** @vitest-environment node */

import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-no-unknown-casts.mjs");

function runScannerInTempRepo(
  files: Record<string, string>,
  deletedFiles: string[] = []
) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-unknown-cast-scan-"));

  try {
    execFileSync("git", ["init"], { cwd: tempDir, stdio: "ignore" });

    for (const [filePath, contents] of Object.entries(files)) {
      const absolutePath = join(tempDir, filePath);
      mkdirSync(dirname(absolutePath), { recursive: true });
      writeFileSync(absolutePath, contents);
    }

    execFileSync("git", ["add", "."], { cwd: tempDir, stdio: "ignore" });

    for (const filePath of deletedFiles) {
      unlinkSync(join(tempDir, filePath));
    }

    return spawnSync(process.execPath, [scriptPath], {
      cwd: tempDir,
      encoding: "utf8",
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

describe("check-no-unknown-casts", () => {
  it("detects unsafe unknown casts in tracked src production files", () => {
    const result = runScannerInTempRepo({
      "src/lib/example.ts": `
        export function coerce(value: unknown) {
          return value as unknown as { id: string };
        }
      `,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("src/lib/example.ts:3");
    expect(result.stderr).toContain("as unknown as");
  });

  it("ignores tests, mocks, and comment-only mentions", () => {
    const result = runScannerInTempRepo({
      "src/lib/__mocks__/fixture.ts": `
        export const mockValue = value as unknown as { id: string };
      `,
      "src/lib/example.test.ts": `
        export const testValue = value as unknown as { id: string };
      `,
      "src/lib/example.ts": `
        // value as unknown as { id: string }
        /*
         * value as unknown as { id: string }
         */
        export const ok = 1;
      `,
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no 'as unknown as' casts found");
  });

  it("skips tracked files that no longer exist in the working tree", () => {
    const result = runScannerInTempRepo(
      {
        "src/lib/deleted.ts": `
          export const deletedValue = value as unknown as { id: string };
        `,
        "src/lib/kept.ts": "export const kept = 1;\n",
      },
      ["src/lib/deleted.ts"]
    );

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no 'as unknown as' casts found");
  });
});
