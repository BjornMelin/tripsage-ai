/**
 * @fileoverview Verifies coverage thresholds for critical surfaces from coverage-final.json.
 *
 * This is intentionally lightweight and dependency-free: it reads Istanbul JSON coverage output
 * produced by Vitest (v8 provider) and computes aggregate coverage for a small set of
 * high-risk areas (auth, payments, keys, webhooks, AI tool routing).
 *
 * Run after `pnpm test:coverage` (or any Vitest run that emits `coverage/coverage-final.json`).
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { EXCLUDED_PATH_PARTS } from "./excluded-path-parts.mjs";

const DEFAULT_COVERAGE_PATH = "coverage/coverage-final.json";

const coverPath = process.argv[2] ?? DEFAULT_COVERAGE_PATH;

function readCoverageJson(filePath) {
  try {
    const raw = readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to read coverage JSON at ${filePath}: ${message}`);
  }
}

function normalizePath(filePath) {
  return String(filePath).replaceAll("\\", "/");
}

const PROJECT_ROOT = process.cwd();

function toRelativeProjectPath(filePath) {
  if (path.isAbsolute(filePath)) {
    return normalizePath(path.relative(PROJECT_ROOT, filePath));
  }
  return normalizePath(filePath);
}

function buildCoveredRelativePaths(coverage) {
  const set = new Set();
  for (const rawFilePath of Object.keys(coverage)) {
    set.add(toRelativeProjectPath(rawFilePath));
  }
  return set;
}

const INCLUDED_FILE_RE = /\.(c|m)?[tj]sx?$/;

function isExcludedSourceFile(filePath) {
  const normalized = normalizePath(filePath);
  if (!INCLUDED_FILE_RE.test(normalized)) return true;
  if (!normalized.startsWith("src/")) return true;
  if (normalized.includes(".test.") || normalized.includes(".spec.")) return true;
  return EXCLUDED_PATH_PARTS.some((part) => normalized.includes(part));
}

function walkSourceFiles(rootDir) {
  const out = [];
  for (const entry of readdirSync(rootDir)) {
    const full = path.join(rootDir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      out.push(...walkSourceFiles(full));
      continue;
    }
    if (!st.isFile()) continue;
    const rel = normalizePath(path.relative(PROJECT_ROOT, full));
    if (!isExcludedSourceFile(rel)) out.push(rel);
  }
  return out;
}

function findMissingGroupFiles(coveredRelativePaths, roots) {
  const isErrno = (error, code) =>
    Boolean(
      error &&
        typeof error === "object" &&
        "code" in error &&
        (error.code === code || String(error.code) === code)
    );

  const missingRoots = [];
  const expectedFiles = roots.flatMap((root) => {
    try {
      return walkSourceFiles(root);
    } catch (error) {
      if (isErrno(error, "ENOENT")) {
        missingRoots.push(root);
        return [];
      }
      throw error;
    }
  });

  if (missingRoots.length > 0) {
    throw new Error(
      "Critical surface root directory not found:\n" +
        missingRoots.map((root) => `- ${root}`).join("\n") +
        "\n\nUpdate scripts/check-coverage-critical.mjs GROUPS[].roots if surfaces were moved/renamed."
    );
  }
  const missing = expectedFiles.filter(
    (filePath) => !coveredRelativePaths.has(filePath)
  );
  return { expectedFiles, missing };
}

function computeCoverageForPrefixes(coverage, prefixes) {
  let stmtTotal = 0;
  let stmtCovered = 0;
  let fnTotal = 0;
  let fnCovered = 0;
  let brTotal = 0;
  let brCovered = 0;
  let lineTotal = 0;
  let lineCovered = 0;
  let files = 0;

  for (const rawFilePath of Object.keys(coverage)) {
    const filePath = normalizePath(rawFilePath);
    if (!prefixes.some((prefix) => filePath.includes(prefix))) continue;

    const entry = coverage[rawFilePath];
    if (!entry || typeof entry !== "object") continue;
    files += 1;

    const lineSeen = new Map();

    if (entry.s && entry.statementMap) {
      for (const [id, count] of Object.entries(entry.s)) {
        stmtTotal += 1;
        if ((count ?? 0) > 0) stmtCovered += 1;

        const map = entry.statementMap[id];
        const line = map?.start?.line;
        if (typeof line === "number") {
          const prev = lineSeen.get(line) ?? false;
          lineSeen.set(line, prev || (count ?? 0) > 0);
        }
      }
    }

    if (entry.f) {
      for (const count of Object.values(entry.f)) {
        fnTotal += 1;
        if ((count ?? 0) > 0) fnCovered += 1;
      }
    }

    if (entry.b) {
      for (const counts of Object.values(entry.b)) {
        if (!Array.isArray(counts)) continue;
        brTotal += counts.length;
        for (const count of counts) {
          if ((count ?? 0) > 0) brCovered += 1;
        }
      }
    }

    lineTotal += lineSeen.size;
    for (const covered of lineSeen.values()) {
      if (covered) lineCovered += 1;
    }
  }

  const pct = (covered, total) => (total === 0 ? 100 : (covered / total) * 100);
  const round = (value) => Math.round(value * 100) / 100;

  return {
    branches: round(pct(brCovered, brTotal)),
    files,
    functions: round(pct(fnCovered, fnTotal)),
    lines: round(pct(lineCovered, lineTotal)),
    statements: round(pct(stmtCovered, stmtTotal)),
  };
}

const coverage = readCoverageJson(coverPath);
const coveredRelativePaths = buildCoveredRelativePaths(coverage);

const GROUPS = [
  {
    id: "auth",
    prefixes: ["/src/app/auth/", "/src/lib/auth/"],
    roots: ["src/app/auth", "src/lib/auth"],
    thresholds: { branches: 50, functions: 85, lines: 80, statements: 80 },
  },
  {
    id: "payments",
    prefixes: ["/src/lib/payments/"],
    roots: ["src/lib/payments"],
    thresholds: { branches: 95, functions: 95, lines: 95, statements: 95 },
  },
  {
    id: "keys",
    prefixes: ["/src/app/api/keys/"],
    roots: ["src/app/api/keys"],
    thresholds: { branches: 60, functions: 70, lines: 75, statements: 75 },
  },
  {
    id: "webhooks",
    prefixes: ["/src/lib/webhooks/", "/src/app/api/hooks/", "/src/lib/qstash/"],
    roots: ["src/lib/webhooks", "src/app/api/hooks", "src/lib/qstash"],
    thresholds: { branches: 55, functions: 70, lines: 70, statements: 70 },
  },
  {
    id: "ai_agents",
    prefixes: ["/src/ai/agents/"],
    roots: ["src/ai/agents"],
    thresholds: { branches: 50, functions: 57, lines: 59, statements: 58 },
  },
  {
    id: "ai_tool_routing",
    prefixes: ["/src/ai/tools/", "/src/ai/lib/", "/src/app/api/chat/"],
    roots: ["src/ai/tools", "src/ai/lib", "src/app/api/chat"],
    thresholds: { branches: 50, functions: 65, lines: 65, statements: 65 },
  },
];

const results = GROUPS.map((group) => ({
  id: group.id,
  ...findMissingGroupFiles(coveredRelativePaths, group.roots),
  thresholds: group.thresholds,
  ...computeCoverageForPrefixes(coverage, group.prefixes),
}));

const failures = [];

for (const result of results) {
  const { thresholds } = result;
  if (result.missing.length > 0) {
    failures.push({
      actual: result.missing.length,
      expected: 0,
      group: result.id,
      metric: "missing_files",
    });
  }
  for (const key of Object.keys(thresholds)) {
    const actual = result[key];
    const expected = thresholds[key];
    if (typeof actual !== "number" || typeof expected !== "number") continue;
    if (actual < expected) {
      failures.push({
        actual,
        expected,
        group: result.id,
        metric: key,
      });
    }
  }
}

function padRight(str, width) {
  return String(str).padEnd(width, " ");
}

const header =
  padRight("group", 16) +
  padRight("files", 7) +
  padRight("missing", 9) +
  padRight("stmts", 8) +
  padRight("br", 8) +
  padRight("fn", 8) +
  padRight("lines", 8);

process.stdout.write(`${header}\n`);
process.stdout.write(`${"-".repeat(header.length)}\n`);

for (const row of results) {
  process.stdout.write(
    padRight(row.id, 16) +
      padRight(row.files, 7) +
      padRight(row.missing.length, 9) +
      padRight(row.statements, 8) +
      padRight(row.branches, 8) +
      padRight(row.functions, 8) +
      padRight(row.lines, 8) +
      "\n"
  );
}

if (failures.length > 0) {
  process.stderr.write("\nCoverage below critical thresholds:\n");
  for (const failure of failures) {
    if (failure.metric === "missing_files") {
      process.stderr.write(
        `- ${failure.group}.missing_files: ${failure.actual} missing\n`
      );
      continue;
    }
    process.stderr.write(
      `- ${failure.group}.${failure.metric}: ${failure.actual}% < ${failure.expected}%\n`
    );
  }

  const missingGroups = results.filter((r) => r.missing.length > 0);
  if (missingGroups.length > 0) {
    process.stderr.write(
      "\nMissing critical-surface source files from coverage output.\n" +
        "These files are effectively unmeasured (likely untested/unimported).\n" +
        "Add/extend tests so they are exercised, or adjust critical-surface scopes.\n\n"
    );
    for (const group of missingGroups) {
      process.stderr.write(`- ${group.id} (missing ${group.missing.length}):\n`);
      for (const filePath of group.missing.slice(0, 25)) {
        process.stderr.write(`  - ${filePath}\n`);
      }
      if (group.missing.length > 25) {
        process.stderr.write(`  ...and ${group.missing.length - 25} more\n`);
      }
    }
  }
  process.exit(1);
}

process.stdout.write("\nOK: critical coverage thresholds satisfied.\n");
