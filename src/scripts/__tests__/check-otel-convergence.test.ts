/** @vitest-environment node */

import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const sourceScriptPath = join(process.cwd(), "scripts/check-otel-convergence.mjs");
const sourceScript = readFileSync(sourceScriptPath, "utf8");

const baseDependencies: Record<string, string> = {
  "@opentelemetry/context-zone": "2.7.1",
  "@opentelemetry/exporter-trace-otlp-http": "0.218.0",
  "@opentelemetry/instrumentation": "0.218.0",
  "@opentelemetry/instrumentation-fetch": "0.218.0",
  "@opentelemetry/resources": "2.7.1",
  "@opentelemetry/sdk-trace-base": "2.7.1",
  "@opentelemetry/sdk-trace-web": "2.7.1",
  "import-in-the-middle": "3.0.1",
  "require-in-the-middle": "8.0.1",
};

function createLockfile(entries: readonly string[]) {
  return `lockfileVersion: '9.0'

packages:
${entries.map((entry) => `  '${entry}':\n    resolution: {integrity: sha512-test}`).join("\n")}
`;
}

function convergedLockfile() {
  return createLockfile([
    "@opentelemetry/context-zone@2.7.1",
    "@opentelemetry/core@2.7.1",
    "@opentelemetry/exporter-trace-otlp-http@0.218.0",
    "@opentelemetry/instrumentation-fetch@0.218.0",
    "@opentelemetry/instrumentation@0.218.0",
    "@opentelemetry/resources@2.7.1",
    "@opentelemetry/sdk-trace-base@2.7.1",
    "@opentelemetry/sdk-trace-web@2.7.1",
    "import-in-the-middle@3.0.1",
    "require-in-the-middle@8.0.1",
  ]);
}

function runGuardInTempProject(
  dependencies: Record<string, string>,
  lockfileText = convergedLockfile()
) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-otel-convergence-"));

  try {
    const scriptsDir = join(tempDir, "scripts");
    mkdirSync(scriptsDir, { recursive: true });
    writeFileSync(join(scriptsDir, "check-otel-convergence.mjs"), sourceScript);
    writeFileSync(
      join(tempDir, "package.json"),
      `${JSON.stringify({ dependencies }, null, 2)}\n`
    );
    writeFileSync(join(tempDir, "pnpm-lock.yaml"), lockfileText);

    return spawnSync(
      process.execPath,
      [join(scriptsDir, "check-otel-convergence.mjs")],
      {
        cwd: tempDir,
        encoding: "utf8",
      }
    );
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

describe("check-otel-convergence", () => {
  it("accepts converged direct dependencies and resolved lockfile entries", () => {
    const result = runGuardInTempProject(baseDependencies);

    expect(result.status).toBe(0);
    expect(result.stdout).toContain(
      "OK: OpenTelemetry/runtime dependency convergence verified"
    );
  });

  it("detects direct OpenTelemetry core dependency version drift", () => {
    const result = runGuardInTempProject({
      ...baseDependencies,
      "@opentelemetry/resources": "2.7.2",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("OTEL dependency convergence check failed");
    expect(result.stderr).toContain(
      "OpenTelemetry core runtime dependencies must share one declared version"
    );
    expect(result.stderr).toContain("@opentelemetry/resources@2.7.2");
  });

  it("detects multiple resolved versions for monitored lockfile packages", () => {
    const result = runGuardInTempProject(
      baseDependencies,
      createLockfile([
        "@opentelemetry/context-zone@2.7.1",
        "@opentelemetry/core@2.7.1",
        "@opentelemetry/core@2.7.2",
        "@opentelemetry/exporter-trace-otlp-http@0.218.0",
        "@opentelemetry/instrumentation-fetch@0.218.0",
        "@opentelemetry/instrumentation@0.218.0",
        "@opentelemetry/resources@2.7.1",
        "@opentelemetry/sdk-trace-base@2.7.1",
        "@opentelemetry/sdk-trace-web@2.7.1",
        "import-in-the-middle@3.0.1",
        "require-in-the-middle@8.0.1",
      ])
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "@opentelemetry/core resolves to multiple versions in lockfile: 2.7.1, 2.7.2"
    );
  });

  it("detects missing runtime shim dependencies", () => {
    const dependencies = Object.fromEntries(
      Object.entries(baseDependencies).filter(
        ([name]) => name !== "import-in-the-middle"
      )
    );
    const result = runGuardInTempProject(dependencies);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "Missing required dependency `import-in-the-middle` in package.json"
    );
  });

  it("detects mismatched resolved versions", () => {
    const result = runGuardInTempProject(
      baseDependencies,
      createLockfile([
        "@opentelemetry/context-zone@2.7.1",
        "@opentelemetry/core@2.7.1",
        "@opentelemetry/exporter-trace-otlp-http@0.218.0",
        "@opentelemetry/instrumentation-fetch@0.218.0",
        "@opentelemetry/instrumentation@0.218.0",
        "@opentelemetry/resources@2.7.1",
        "@opentelemetry/sdk-trace-base@2.7.1",
        "@opentelemetry/sdk-trace-web@2.7.1",
        "import-in-the-middle@3.0.2",
        "require-in-the-middle@8.0.1",
      ])
    );

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "import-in-the-middle resolves to 3.0.2 but package.json expects 3.0.1"
    );
  });
});
