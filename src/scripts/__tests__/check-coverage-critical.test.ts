/** @vitest-environment node */

import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-coverage-critical.mjs");

const criticalFiles = [
  "src/app/auth/page.ts",
  "src/lib/auth/server.ts",
  "src/lib/payments/checkout.ts",
  "src/app/api/keys/route.ts",
  "src/lib/webhooks/handler.ts",
  "src/app/api/hooks/cache/route.ts",
  "src/lib/qstash/client.ts",
  "src/ai/agents/router.ts",
  "src/ai/tools/flights.ts",
  "src/ai/lib/tool-factory.ts",
  "src/app/api/chat/route.ts",
];

type CoverageCounts = {
  branch?: number;
  function?: number;
  statement?: number;
};

function writeFixtureFiles(root: string, files: readonly string[]) {
  for (const filePath of files) {
    const absolutePath = join(root, filePath);
    mkdirSync(dirname(absolutePath), { recursive: true });
    writeFileSync(absolutePath, "export const covered = true;\n");
  }
}

function coverageEntry(counts: CoverageCounts = {}) {
  return {
    b: {
      "0": [counts.branch ?? 1],
    },
    branchMap: {
      "0": {
        line: 1,
        locations: [{ line: 1 }],
        type: "if",
      },
    },
    f: {
      "0": counts.function ?? 1,
    },
    fnMap: {
      "0": {
        decl: { line: 1 },
        line: 1,
        loc: { line: 1 },
        name: "covered",
      },
    },
    s: {
      "0": counts.statement ?? 1,
    },
    statementMap: {
      "0": {
        start: { line: 1 },
      },
    },
  };
}

function coverageForFiles(root: string, files: readonly string[]) {
  return Object.fromEntries(
    files.map((filePath) => [join(root, filePath), coverageEntry()])
  );
}

function runCoverageCheck({
  coverage,
  sourceFiles = criticalFiles,
}: {
  coverage: Record<string, unknown>;
  sourceFiles?: readonly string[];
}) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-critical-coverage-"));

  try {
    writeFixtureFiles(tempDir, sourceFiles);
    const coveragePath = join(tempDir, "coverage-final.json");
    writeFileSync(coveragePath, `${JSON.stringify(coverage, null, 2)}\n`);

    return spawnSync(process.execPath, [scriptPath, coveragePath], {
      cwd: tempDir,
      encoding: "utf8",
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

describe("check-coverage-critical", () => {
  it("accepts coverage that includes every critical file above thresholds", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "tripsage-critical-coverage-ok-"));

    try {
      writeFixtureFiles(tempDir, criticalFiles);
      const coveragePath = join(tempDir, "coverage-final.json");
      writeFileSync(
        coveragePath,
        `${JSON.stringify(coverageForFiles(tempDir, criticalFiles), null, 2)}\n`
      );

      const result = spawnSync(process.execPath, [scriptPath, coveragePath], {
        cwd: tempDir,
        encoding: "utf8",
      });

      expect(result.status).toBe(0);
      expect(result.stdout).toContain("auth");
      expect(result.stdout).toContain("OK: critical coverage thresholds satisfied");
    } finally {
      rmSync(tempDir, { force: true, recursive: true });
    }
  });

  it("fails when a critical surface falls below its configured threshold", () => {
    const tempDir = mkdtempSync(
      join(tmpdir(), "tripsage-critical-coverage-threshold-")
    );

    try {
      writeFixtureFiles(tempDir, criticalFiles);
      const coverage = coverageForFiles(tempDir, criticalFiles);
      coverage[join(tempDir, "src/app/api/keys/route.ts")] = coverageEntry({
        branch: 0,
        function: 0,
        statement: 0,
      });

      const coveragePath = join(tempDir, "coverage-final.json");
      writeFileSync(coveragePath, `${JSON.stringify(coverage, null, 2)}\n`);

      const result = spawnSync(process.execPath, [scriptPath, coveragePath], {
        cwd: tempDir,
        encoding: "utf8",
      });

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("Coverage below critical thresholds");
      expect(result.stderr).toContain("keys.functions");
    } finally {
      rmSync(tempDir, { force: true, recursive: true });
    }
  });

  it("fails when a critical source file is missing from coverage output", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "tripsage-critical-coverage-missing-"));

    try {
      writeFixtureFiles(tempDir, criticalFiles);
      const coveredFiles = criticalFiles.filter(
        (filePath) => filePath !== "src/lib/auth/server.ts"
      );
      const coveragePath = join(tempDir, "coverage-final.json");
      writeFileSync(
        coveragePath,
        `${JSON.stringify(coverageForFiles(tempDir, coveredFiles), null, 2)}\n`
      );

      const result = spawnSync(process.execPath, [scriptPath, coveragePath], {
        cwd: tempDir,
        encoding: "utf8",
      });

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("auth.missing_files");
      expect(result.stderr).toContain("src/lib/auth/server.ts");
    } finally {
      rmSync(tempDir, { force: true, recursive: true });
    }
  });

  it("fails loudly when a configured critical root was moved or removed", () => {
    const result = runCoverageCheck({
      coverage: coverageForFiles(tmpdir(), criticalFiles),
      sourceFiles: criticalFiles.filter(
        (filePath) => !filePath.startsWith("src/lib/payments/")
      ),
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("Critical surface root directory not found");
    expect(result.stderr).toContain("src/lib/payments");
  });
});
