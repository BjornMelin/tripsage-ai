/**
 * @fileoverview Enforces TripSage's Zod v4 style rules (diff-based by default).
 *
 * Why:
 * - Repo contract prefers Zod v4 top-level string helpers (`z.uuid()`, `z.email()`, `z.iso.datetime()`)
 *   over method-style chains (`z.string().uuid()`, `z.string().email()`, `z.string().datetime()`).
 *
 * Notes:
 * - Only checks files changed in the current diff (BASE_REF...HEAD, defaulting to origin/main...HEAD or main...HEAD).
 * - Use `--full` to scan all tracked `src/**` files.
 * - Excludes tests/mocks.
 * - Allow an exception by adding `zod-v4-ok:` on the violating line with a short justification.
 */

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

import { EXCLUDED_PATH_PARTS } from "./excluded-path-parts.mjs";

const ALLOWLIST_MARKER = "zod-v4-ok:";
const ARGS = new Set(process.argv.slice(2));
const MODE = ARGS.has("--full") ? "full" : "diff";

const CHECKED_FILE_RE = /\.(c|m)?[tj]sx?$/;

function isExcludedPath(filePath) {
  if (!filePath.startsWith("src/")) return true;
  if (!CHECKED_FILE_RE.test(filePath)) return true;
  if (EXCLUDED_PATH_PARTS.some((part) => filePath.includes(part))) return true;
  return filePath.includes(".test.") || filePath.includes(".spec.");
}

function runGitDiffNameOnly(range) {
  return execFileSync("git", ["diff", "--name-only", range, "--", "src"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function getTrackedFiles() {
  const out = execFileSync("git", ["ls-files", "--", "src"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return out
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function getChangedFiles() {
  const configuredBase = process.env.BASE_REF?.trim();
  const candidates = [
    ...(configuredBase ? [`${configuredBase}...HEAD`] : []),
    "origin/main...HEAD",
    "main...HEAD",
  ];
  const errors = [];

  for (const range of candidates) {
    try {
      const out = runGitDiffNameOnly(range);
      return out
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
    } catch (error) {
      errors.push({ error, range });
    }
  }

  const details = errors
    .map((entry) => {
      const stderr =
        entry.error && typeof entry.error === "object" && "stderr" in entry.error
          ? String(entry.error.stderr || "")
          : "";
      return `- ${entry.range}${stderr ? `: ${stderr.trim()}` : ""}`;
    })
    .join("\n");

  throw new Error(
    `Failed to compute diff range.\nTried:\n${details}\n\n` +
      "Ensure the base branch is available locally (e.g. fetch origin/main)."
  );
}

function readText(filePath) {
  try {
    return readFileSync(filePath, "utf8");
  } catch (error) {
    // Deleted files can appear in git diff but won't exist on disk.
    if (
      error &&
      typeof error === "object" &&
      "code" in error &&
      (error.code === "ENOENT" || String(error.code) === "ENOENT")
    ) {
      return null;
    }
    throw error;
  }
}

function isInBlockCommentPrefix(text, index) {
  const before = text.slice(0, index);
  const lastOpen = before.lastIndexOf("/*");
  if (lastOpen === -1) return false;
  const lastClose = before.lastIndexOf("*/");
  return lastClose < lastOpen;
}

function getLineAndColumn(text, index) {
  const before = text.slice(0, index);
  const lastNewline = before.lastIndexOf("\n");
  const line = before.split("\n").length; // 1-based
  const column = index - (lastNewline + 1) + 1; // 1-based
  return { column, line };
}

function getLineText(text, index) {
  const start = text.lastIndexOf("\n", index) + 1;
  const end = text.indexOf("\n", index);
  if (end === -1) return text.slice(start);
  return text.slice(start, end);
}

function shouldIgnoreMatch(text, matchIndex) {
  const lineText = getLineText(text, matchIndex);
  const trimmed = lineText.trimStart();
  if (trimmed.startsWith("//") || trimmed.startsWith("*")) return true;
  if (trimmed.includes(ALLOWLIST_MARKER)) return true;
  if (isInBlockCommentPrefix(text, matchIndex)) return true;
  return false;
}

const RULES = [
  {
    id: "zod-string-email",
    message: "Use top-level `z.email()` (not `z.string().email()`).",
    pattern: /\bz\s*\.\s*string\s*\(\s*(?:\{[\s\S]*?\}\s*)?\)\s*\.\s*email\s*\(/g,
  },
  {
    id: "zod-string-uuid",
    message: "Use top-level `z.uuid()` (not `z.string().uuid()`).",
    pattern: /\bz\s*\.\s*string\s*\(\s*(?:\{[\s\S]*?\}\s*)?\)\s*\.\s*uuid\s*\(/g,
  },
  {
    id: "zod-string-url",
    message: "Use top-level `z.url()` (not `z.string().url()`).",
    pattern: /\bz\s*\.\s*string\s*\(\s*(?:\{[\s\S]*?\}\s*)?\)\s*\.\s*url\s*\(/g,
  },
  {
    id: "zod-string-datetime",
    message: "Use `z.iso.datetime()` (not `z.string().datetime()`).",
    pattern: /\bz\s*\.\s*string\s*\(\s*(?:\{[\s\S]*?\}\s*)?\)\s*\.\s*datetime\s*\(/g,
  },
];

function scanText(filePath, text) {
  const violations = [];

  for (const rule of RULES) {
    for (const match of text.matchAll(rule.pattern)) {
      const matchIndex = match.index ?? -1;
      if (matchIndex < 0) continue;
      if (shouldIgnoreMatch(text, matchIndex)) continue;

      const { line, column } = getLineAndColumn(text, matchIndex);
      const lineText = getLineText(text, matchIndex).trimEnd();

      violations.push({
        column,
        filePath,
        line,
        lineText,
        message: rule.message,
        ruleId: rule.id,
      });
    }
  }

  return violations;
}

const candidateFiles = MODE === "full" ? getTrackedFiles() : getChangedFiles();
const checkedFiles = candidateFiles.filter((filePath) => !isExcludedPath(filePath));

const violations = [];

for (const filePath of checkedFiles) {
  const text = readText(filePath);
  if (text === null) continue;
  violations.push(...scanText(filePath, text));
}

if (violations.length > 0) {
  const formatted = violations
    .map(
      (v) =>
        `- ${v.filePath}:${v.line}:${v.column} ${v.ruleId}: ${v.message}\n  ${v.lineText}`
    )
    .join("\n");

  process.stderr.write(
    `Found non-compliant Zod v4 usage in ${
      MODE === "full" ? "tracked" : "changed"
    } non-test code.\n\n` +
      "Preferred patterns:\n" +
      "  z.email()\n" +
      "  z.uuid()\n" +
      "  z.url()\n" +
      "  z.iso.datetime()\n\n" +
      `If absolutely necessary, add '${ALLOWLIST_MARKER}' on the line with a short justification.\n\n` +
      formatted +
      "\n"
  );
  process.exit(1);
}

process.stdout.write("OK: no Zod v4 style violations detected.\n");
