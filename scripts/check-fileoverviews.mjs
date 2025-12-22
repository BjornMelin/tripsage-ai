/**
 * @fileoverview Rejects multi-line `@fileoverview` blocks in non-test `src/**` code (diff-based).
 *
 * Goal: prevent “LLM slop” header drift by enforcing that touched files keep `@fileoverview`
 * to a single, stable sentence. Detailed docs belong in `docs/` (not per-file headers).
 *
 * Notes:
 * - Only checks files changed in the current diff (BASE_REF...HEAD, defaulting to origin/main...HEAD or main...HEAD).
 * - Use `--full` to scan all tracked `src/**` files.
 * - Excludes tests/mocks.
 * - Allow an exception by adding `fileoverview-ok:` on the `@fileoverview` line with a short justification.
 */

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

import { EXCLUDED_PATH_PARTS } from "./excluded-path-parts.mjs";

const ALLOWLIST_MARKER = "fileoverview-ok:";
const MODE = new Set(process.argv.slice(2)).has("--full") ? "full" : "diff";

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
    // Handle files deleted between listing and reading (rare race condition)
    if (
      error &&
      typeof error === "object" &&
      "code" in error &&
      // NodeJS errno codes are strings like "ENOENT"
      (error.code === "ENOENT" || String(error.code) === "ENOENT")
    ) {
      const message = error instanceof Error ? error.message : String(error);
      process.stderr.write(
        `[check-fileoverviews] skipped missing file: ${filePath} (${message})\n`
      );
      return null;
    }
    throw error;
  }
}

function extractFileoverviewBlock(lines, filePath) {
  const maxScan = Math.min(80, lines.length);
  let fileoverviewLine = -1;

  for (let i = 0; i < maxScan; i += 1) {
    if (lines[i]?.includes("@fileoverview")) {
      fileoverviewLine = i;
      break;
    }
  }

  if (fileoverviewLine === -1) return null;

  // Find the start of the JSDoc block.
  let start = -1;
  for (let i = fileoverviewLine; i >= 0; i -= 1) {
    if (lines[i]?.includes("/**")) {
      start = i;
      break;
    }
  }

  if (start === -1) {
    return {
      filePath,
      reason: "Found @fileoverview without a JSDoc block start (/**).",
    };
  }

  // Find the end of the JSDoc block.
  let end = -1;
  for (let i = fileoverviewLine; i < lines.length; i += 1) {
    if (lines[i]?.includes("*/")) {
      end = i;
      break;
    }
  }

  if (end === -1) {
    return {
      filePath,
      reason: "Found @fileoverview without a JSDoc block end (*/).",
    };
  }

  return {
    end,
    filePath,
    lines: lines.slice(start, end + 1),
    start,
  };
}

function normalizeDocLine(rawLine) {
  const trimmed = rawLine.trim();
  if (trimmed === "/**" || trimmed === "*/") return "";
  if (!trimmed.startsWith("*")) return trimmed;
  const withoutStar = trimmed.slice(1).trimStart();
  return withoutStar;
}

function validateFileoverviewBlock(block) {
  const normalized = block.lines.map(normalizeDocLine);
  const fileoverviewLines = normalized.filter((line) =>
    line.startsWith("@fileoverview")
  );

  if (fileoverviewLines.length === 0) {
    return { ok: false, reason: "Missing @fileoverview line inside extracted block." };
  }

  const fileoverviewLine = fileoverviewLines[0];
  if (fileoverviewLine.includes(ALLOWLIST_MARKER)) {
    return { ok: true };
  }

  // Allow only the @fileoverview line; everything else must be empty.
  const extraContent = normalized.filter((line) => {
    if (!line) return false;
    return !line.startsWith("@fileoverview");
  });

  if (extraContent.length > 0) {
    return {
      ok: false,
      reason:
        "Multi-line @fileoverview block detected. Keep @fileoverview to a single sentence and move details to docs/.",
    };
  }

  // Ensure the @fileoverview line has a description.
  const description = fileoverviewLine.replace("@fileoverview", "").trim();
  if (!description) {
    return { ok: false, reason: "@fileoverview must include a short description." };
  }

  return { ok: true };
}

const candidateFiles = MODE === "full" ? getTrackedFiles() : getChangedFiles();
const changedFiles = candidateFiles.filter((filePath) => !isExcludedPath(filePath));

const violations = [];

for (const filePath of changedFiles) {
  const text = readText(filePath);
  if (text === null) continue; // Skip deleted files
  const lines = text.split("\n");
  const block = extractFileoverviewBlock(lines, filePath);
  if (!block) continue;

  if ("reason" in block) {
    violations.push(block);
    continue;
  }

  const result = validateFileoverviewBlock(block);
  if (!result.ok) {
    violations.push({
      filePath,
      reason: result.reason,
      snippet: block.lines.join("\n"),
    });
  }
}

if (violations.length > 0) {
  process.stderr.write(
    `Found non-compliant @fileoverview headers in ${
      MODE === "full" ? "tracked" : "changed"
    } non-test code.\n\n` +
      "Required format:\n" +
      "  /**\n" +
      "   * @fileoverview One short sentence.\n" +
      "   */\n\n" +
      `If absolutely necessary, add '${ALLOWLIST_MARKER}' on the @fileoverview line with a justification.\n\n`
  );

  for (const v of violations) {
    process.stderr.write(`- ${v.filePath}: ${v.reason}\n`);
    if (v.snippet) {
      process.stderr.write(`${v.snippet}\n\n`);
    }
  }

  process.exit(1);
}

process.stdout.write(
  `OK: no @fileoverview drift detected in ${
    MODE === "full" ? "tracked" : "changed"
  } non-test code.\n`
);
