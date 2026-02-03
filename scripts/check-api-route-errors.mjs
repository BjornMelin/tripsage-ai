/**
 * @fileoverview Enforces route-handler error response helpers in `src/app/api/**`.
 *
 * Repo contract forbids inline JSON error responses like:
 * - `NextResponse.json({ error: "..." }, { status: 4xx/5xx })`
 * - `new Response(JSON.stringify({ error: "..." }), { status: 4xx/5xx })`
 *
 * Use `errorResponse()` (and other helpers) from `@/lib/api/route-helpers` instead.
 *
 * Notes:
 * - Only checks files changed in the current diff (BASE_REF...HEAD, defaulting to origin/main...HEAD or main...HEAD).
 * - Use `--full` to scan all tracked `src/app/api/**` files.
 * - Excludes tests/mocks.
 * - Allow an exception by adding `api-route-error-ok:` on the violating line with a short justification.
 */

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

import { EXCLUDED_PATH_PARTS } from "./excluded-path-parts.mjs";

const ALLOWLIST_MARKER = "api-route-error-ok:";
const ARGS = new Set(process.argv.slice(2));
const MODE = ARGS.has("--full") ? "full" : "diff";

const CHECKED_FILE_RE = /\.(c|m)?[tj]sx?$/;

function isExcludedPath(filePath) {
  if (!filePath.startsWith("src/app/api/")) return true;
  if (!CHECKED_FILE_RE.test(filePath)) return true;
  if (EXCLUDED_PATH_PARTS.some((part) => filePath.includes(part))) return true;
  return filePath.includes(".test.") || filePath.includes(".spec.");
}

function runGitDiffNameOnly(range) {
  return execFileSync("git", ["diff", "--name-only", range, "--", "src/app/api"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function getTrackedFiles() {
  const out = execFileSync("git", ["ls-files", "--", "src/app/api"], {
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

function scanBalancedObject(text, startIndex) {
  if (text[startIndex] !== "{") return null;

  let i = startIndex;
  let depth = 0;
  let mode = "code"; // code | line_comment | block_comment | sq | dq | bt
  let templateExprDepth = 0;

  while (i < text.length) {
    const ch = text[i];
    const next = i + 1 < text.length ? text[i + 1] : "";

    if (mode === "line_comment") {
      if (ch === "\n") mode = "code";
      i += 1;
      continue;
    }

    if (mode === "block_comment") {
      if (ch === "*" && next === "/") {
        mode = "code";
        i += 2;
        continue;
      }
      i += 1;
      continue;
    }

    if (mode === "sq" || mode === "dq") {
      if (ch === "\\" && next) {
        i += 2;
        continue;
      }
      const quote = mode === "sq" ? "'" : '"';
      if (ch === quote) mode = "code";
      i += 1;
      continue;
    }

    if (mode === "bt") {
      if (ch === "\\" && next) {
        i += 2;
        continue;
      }
      if (ch === "`" && templateExprDepth === 0) {
        mode = "code";
        i += 1;
        continue;
      }
      // Track `${ ... }` expressions inside template strings so we don't miscount braces.
      if (ch === "$" && next === "{") {
        templateExprDepth += 1;
        i += 2;
        continue;
      }
      if (templateExprDepth > 0) {
        if (ch === "{") templateExprDepth += 1;
        if (ch === "}") templateExprDepth -= 1;
      }
      i += 1;
      continue;
    }

    // code
    if (ch === "/" && next === "/") {
      mode = "line_comment";
      i += 2;
      continue;
    }
    if (ch === "/" && next === "*") {
      mode = "block_comment";
      i += 2;
      continue;
    }
    if (ch === "'") {
      mode = "sq";
      i += 1;
      continue;
    }
    if (ch === '"') {
      mode = "dq";
      i += 1;
      continue;
    }
    if (ch === "`") {
      mode = "bt";
      templateExprDepth = 0;
      i += 1;
      continue;
    }

    if (ch === "{") {
      if (depth === 0 && i !== startIndex) {
        // Nested object; still counted.
      }
      depth += 1;
    } else if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        return { endIndex: i, text: text.slice(startIndex, i + 1) };
      }
    }

    i += 1;
  }

  return null;
}

function findObjectLiteralAfter(text, startIndex) {
  let i = startIndex;
  while (i < text.length) {
    const ch = text[i];
    if (/\s/.test(ch)) {
      i += 1;
      continue;
    }
    if (ch === "{") return i;
    return null;
  }
  return null;
}

function isErrorObjectLiteral(objectLiteralText) {
  // We only care about top-level payload objects that include an `error:` property.
  // If a route uses an error helper, this won't match.
  return /\berror\b\s*:/.test(objectLiteralText);
}

function scanForbiddenNextResponseJson(text) {
  const matches = [];
  const needle = "NextResponse.json";
  let index = 0;

  while (index < text.length) {
    const at = text.indexOf(needle, index);
    if (at === -1) break;
    index = at + needle.length;

    const openParen = text.indexOf("(", index);
    if (openParen === -1) continue;

    const objectStart = findObjectLiteralAfter(text, openParen + 1);
    if (objectStart === null) continue;

    const object = scanBalancedObject(text, objectStart);
    if (!object) continue;

    if (!isErrorObjectLiteral(object.text)) continue;

    matches.push({ index: at, kind: "NextResponse.json", objectText: object.text });
  }

  return matches;
}

function scanForbiddenNewResponseJson(text) {
  const matches = [];
  const needle = "new Response";
  let index = 0;

  while (index < text.length) {
    const at = text.indexOf(needle, index);
    if (at === -1) break;
    index = at + needle.length;

    // Quick filter: look for JSON.stringify soon after.
    const stringifyAt = text.indexOf("JSON.stringify", at);
    if (stringifyAt === -1 || stringifyAt - at > 250) continue;

    const openParen = text.indexOf("(", stringifyAt);
    if (openParen === -1) continue;

    const objectStart = findObjectLiteralAfter(text, openParen + 1);
    if (objectStart === null) continue;

    const object = scanBalancedObject(text, objectStart);
    if (!object) continue;

    if (!isErrorObjectLiteral(object.text)) continue;

    matches.push({
      index: at,
      kind: "new Response(JSON.stringify",
      objectText: object.text,
    });
  }

  return matches;
}

function scanText(filePath, text) {
  const violations = [];
  const all = [
    ...scanForbiddenNextResponseJson(text),
    ...scanForbiddenNewResponseJson(text),
  ];

  for (const match of all) {
    const { line, column } = getLineAndColumn(text, match.index);
    const lineText = getLineText(text, match.index);
    if (lineText.includes(ALLOWLIST_MARKER)) continue;
    const trimmed = lineText.trimStart();
    if (trimmed.startsWith("//") || trimmed.startsWith("*")) continue;

    violations.push({
      column,
      filePath,
      kind: match.kind,
      line,
      lineText: lineText.trimEnd(),
    });
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
      (v) => `- ${v.filePath}:${v.line}:${v.column} ${v.kind}\n  ${v.lineText.trim()}`
    )
    .join("\n");

  process.stderr.write(
    `Found forbidden inline error JSON responses in ${
      MODE === "full" ? "tracked" : "changed"
    } route code.\n\n` +
      "Use `errorResponse()` (or `unauthorizedResponse()`, `forbiddenResponse()`, etc.) from `@/lib/api/route-helpers`.\n\n" +
      `If absolutely necessary, add '${ALLOWLIST_MARKER}' on the violating line with a short justification.\n\n` +
      formatted +
      "\n"
  );
  process.exit(1);
}

process.stdout.write("OK: no forbidden inline route error responses detected.\n");
