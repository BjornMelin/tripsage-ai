/**
 * @fileoverview Rejects new Domain → Lib/Infra imports in `src/domain/**` (diff-based).
 *
 * Domain importing infra is currently legacy and should be burned down.
 * This check prevents new coupling from being introduced while allowing existing
 * legacy imports to be refactored over time.
 */

import { execFileSync } from "node:child_process";

const ALLOWLIST_MARKER = "domain-infra-ok:";

const CHECKED_FILE_RE = /\.(c|m)?[tj]sx?$/;

const EXCLUDED_PATH_PARTS = ["/__tests__/", "src/test/", "src/mocks/", "/__mocks__/"];

const DISALLOWED_IMPORT_PREFIXES = [
  "@/lib/cache/",
  "@/lib/env/",
  "@/lib/idempotency",
  "@/lib/payments/",
  "@/lib/qstash/",
  "@/lib/ratelimit/",
  "@/lib/redis",
  "@/lib/supabase/",
  "@/lib/telemetry/",
];

function isExcludedPath(filePath) {
  if (!filePath.startsWith("src/domain/")) return true;
  if (!CHECKED_FILE_RE.test(filePath)) return true;
  if (EXCLUDED_PATH_PARTS.some((part) => filePath.includes(part))) return true;
  return filePath.includes(".test.") || filePath.includes(".spec.");
}

function runGitDiff(range) {
  return execFileSync("git", ["diff", "--unified=0", range, "--", "src/domain"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function getDiffText() {
  const candidates = ["origin/main...HEAD", "main...HEAD"];
  const errors = [];

  for (const range of candidates) {
    try {
      return runGitDiff(range);
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

function isCommentLine(line) {
  const trimmed = line.trimStart();
  return (
    trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*")
  );
}

function parseDiffForViolations(diffText) {
  const violations = [];
  let currentFile = null;
  let currentFileExcluded = true;

  for (const rawLine of diffText.split("\n")) {
    if (rawLine.startsWith("diff --git ")) {
      const match = /^diff --git a\/(.+?) b\/(.+?)$/.exec(rawLine);
      currentFile = match?.[2] ?? null;
      currentFileExcluded = currentFile ? isExcludedPath(currentFile) : true;
      continue;
    }

    if (!currentFile || currentFileExcluded) continue;

    if (!rawLine.startsWith("+")) continue;
    if (rawLine.startsWith("+++")) continue;

    if (rawLine.includes(ALLOWLIST_MARKER)) continue;

    const line = rawLine.slice(1);
    if (isCommentLine(line)) continue;

    if (!DISALLOWED_IMPORT_PREFIXES.some((prefix) => line.includes(prefix))) continue;

    // Only flag import-ish lines to avoid false positives in text literals.
    const trimmed = line.trimStart();
    const isImportish =
      trimmed.startsWith("import ") ||
      trimmed.startsWith("export ") ||
      trimmed.includes("import(");
    if (!isImportish) continue;

    violations.push({ filePath: currentFile, line });
  }

  return violations;
}

function formatViolations(violations) {
  return violations.map((v) => `- ${v.filePath}: ${v.line.trim()}`).join("\n");
}

const diffText = getDiffText();
const violations = parseDiffForViolations(diffText);

if (violations.length > 0) {
  process.stderr.write(
    "Found new Domain → Lib/Infra imports in src/domain/**.\n" +
      "Prefer moving infra usage to @/lib or wiring at the App/AI layers.\n" +
      `If unavoidable, add an inline justification marker (${ALLOWLIST_MARKER}).\n\n` +
      formatViolations(violations) +
      "\n"
  );
  process.exit(1);
}

process.stdout.write("OK: no new Domain → Lib/Infra imports detected.\n");
