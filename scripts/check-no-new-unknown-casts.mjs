/**
 * @fileoverview Rejects new `as unknown as` casts in non-test `src/**` code (diff-based).
 */

import { execFileSync } from "node:child_process";

const ALLOWLIST_MARKER = "cast-ok:";

const CHECKED_FILE_RE = /\.(c|m)?[tj]sx?$/;

const EXCLUDED_PATH_PARTS = ["/__tests__/", "src/test/", "src/mocks/", "/__mocks__/"];

function isExcludedPath(filePath) {
  if (!filePath.startsWith("src/")) return true;
  if (!CHECKED_FILE_RE.test(filePath)) return true;
  if (EXCLUDED_PATH_PARTS.some((part) => filePath.includes(part))) return true;
  return filePath.includes(".test.") || filePath.includes(".spec.");
}

function runGitDiff(range) {
  return execFileSync("git", ["diff", "--unified=0", range, "--", "src"], {
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

    if (!rawLine.includes("as unknown as")) continue;
    if (rawLine.includes(ALLOWLIST_MARKER)) continue;

    const line = rawLine.slice(1);
    const trimmed = line.trimStart();
    if (trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*"))
      continue;

    violations.push({
      filePath: currentFile,
      line,
    });
  }

  return violations;
}

function formatViolations(violations) {
  return violations.map((v) => `- ${v.filePath}: ${v.line.trim()}`).join("\n");
}

const diffText = getDiffText();
const violations = parseDiffForViolations(diffText);

if (violations.length > 0) {
  console.error(
    `Found new 'as unknown as' casts in non-test code.\n` +
      `Add an inline justification marker (${ALLOWLIST_MARKER}) or remove the cast.\n\n` +
      formatViolations(violations)
  );
  process.exit(1);
}

process.stdout.write("OK: no new 'as unknown as' casts detected.\n");
