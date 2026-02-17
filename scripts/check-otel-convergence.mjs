/**
 * @fileoverview Guards against OpenTelemetry/runtime dependency drift.
 *
 * Enforces:
 * - Shared patch-line convergence for OTEL runtime SDK packages.
 * - Shared patch-line convergence for OTEL instrumentation/exporter packages.
 * - Single resolved version in lockfile for monitored OTEL/runtime modules.
 *
 * This prevents lockfile splits such as OTEL 2.5.0 + 2.5.1 or mixed
 * `import-in-the-middle` majors.
 */

import { readFileSync } from "node:fs";

const PACKAGE_JSON_PATH = new URL("../package.json", import.meta.url);
const LOCKFILE_PATH = new URL("../pnpm-lock.yaml", import.meta.url);

const OTEL_CORE_DIRECT = [
  "@opentelemetry/context-zone",
  "@opentelemetry/resources",
  "@opentelemetry/sdk-trace-base",
  "@opentelemetry/sdk-trace-web",
];

const OTEL_INSTRUMENTATION_DIRECT = [
  "@opentelemetry/exporter-trace-otlp-http",
  "@opentelemetry/instrumentation",
  "@opentelemetry/instrumentation-fetch",
];

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function readJson(pathUrl) {
  return JSON.parse(readFileSync(pathUrl, "utf8"));
}

function unique(values) {
  return [...new Set(values)];
}

function expectSingleDeclaredVersion(dependencies, packageNames, groupLabel, errors) {
  const missing = packageNames.filter((name) => !(name in dependencies));
  if (missing.length > 0) {
    errors.push(
      `Missing ${groupLabel} dependencies in package.json: ${missing.join(", ")}`
    );
    return null;
  }

  const declaredVersions = unique(packageNames.map((name) => dependencies[name]));
  if (declaredVersions.length !== 1) {
    const details = packageNames
      .map((name) => `${name}@${dependencies[name] ?? "MISSING"}`)
      .join(", ");
    errors.push(
      `${groupLabel} dependencies must share one declared version. Found: ${details}`
    );
    return null;
  }

  return declaredVersions[0];
}

function collectLockfileVersions(lockText, packageName) {
  const pattern = new RegExp(
    `^\\s{2}'?${escapeRegExp(packageName)}@([^:'\\s(]+)(?:\\([^\\n]*\\))?'?:`,
    "gm"
  );

  const versions = new Set();
  for (const match of lockText.matchAll(pattern)) {
    versions.add(match[1]);
  }
  return [...versions];
}

const pkg = readJson(PACKAGE_JSON_PATH);
const dependencies = pkg.dependencies ?? {};
const lockText = readFileSync(LOCKFILE_PATH, "utf8");
const errors = [];

const otelCoreVersion = expectSingleDeclaredVersion(
  dependencies,
  OTEL_CORE_DIRECT,
  "OpenTelemetry core runtime",
  errors
);

const otelInstrumentationVersion = expectSingleDeclaredVersion(
  dependencies,
  OTEL_INSTRUMENTATION_DIRECT,
  "OpenTelemetry instrumentation/exporter",
  errors
);

const importInTheMiddleVersion = dependencies["import-in-the-middle"];
if (!importInTheMiddleVersion) {
  errors.push("Missing required dependency `import-in-the-middle` in package.json.");
}

const requireInTheMiddleVersion = dependencies["require-in-the-middle"];
if (!requireInTheMiddleVersion) {
  errors.push("Missing required dependency `require-in-the-middle` in package.json.");
}

const expectedResolvedVersions = new Map(
  Object.entries({
    "@opentelemetry/context-zone": otelCoreVersion,
    "@opentelemetry/core": otelCoreVersion,
    "@opentelemetry/exporter-trace-otlp-http": otelInstrumentationVersion,
    "@opentelemetry/instrumentation": otelInstrumentationVersion,
    "@opentelemetry/instrumentation-fetch": otelInstrumentationVersion,
    "@opentelemetry/resources": otelCoreVersion,
    "@opentelemetry/sdk-trace-base": otelCoreVersion,
    "@opentelemetry/sdk-trace-web": otelCoreVersion,
    "import-in-the-middle": importInTheMiddleVersion,
    "require-in-the-middle": requireInTheMiddleVersion,
  }).filter(([, version]) => typeof version === "string" && version.length > 0)
);

for (const [packageName, expectedVersion] of expectedResolvedVersions) {
  const resolvedVersions = collectLockfileVersions(lockText, packageName);

  if (resolvedVersions.length === 0) {
    errors.push(`No ${packageName}@* entry found in pnpm-lock.yaml.`);
    continue;
  }

  if (resolvedVersions.length > 1) {
    errors.push(
      `${packageName} resolves to multiple versions in lockfile: ${resolvedVersions.join(
        ", "
      )}`
    );
    continue;
  }

  const [resolvedVersion] = resolvedVersions;
  if (resolvedVersion !== expectedVersion) {
    errors.push(
      `${packageName} resolves to ${resolvedVersion} but package.json expects ${expectedVersion}.`
    );
  }
}

if (errors.length > 0) {
  process.stderr.write("OTEL dependency convergence check failed:\n");
  for (const error of errors) {
    process.stderr.write(`- ${error}\n`);
  }
  process.exit(1);
}

process.stdout.write("OK: OpenTelemetry/runtime dependency convergence verified.\n");
