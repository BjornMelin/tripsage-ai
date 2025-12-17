/**
 * @fileoverview Rejects any `as unknown as` casts in non-test `src/**` code (full scan).
 */

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const CHECKED_FILE_RE = /\.(c|m)?[tj]sx?$/;

const EXCLUDED_PATH_PARTS = ["/__tests__/", "src/test/", "src/mocks/", "/__mocks__/"];

function isExcludedPath(filePath) {
  if (!CHECKED_FILE_RE.test(filePath)) return true;
  if (EXCLUDED_PATH_PARTS.some((part) => filePath.includes(part))) return true;
  return (
    filePath.includes(".test.") ||
    filePath.includes(".spec.") ||
    filePath.endsWith(".test.ts") ||
    filePath.endsWith(".test.tsx") ||
    filePath.endsWith(".spec.ts") ||
    filePath.endsWith(".spec.tsx")
  );
}

function listTrackedSrcFiles() {
  const out = execFileSync("git", ["ls-files", "--", "src"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return out
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((filePath) => !isExcludedPath(filePath));
}

function findViolations(filePaths) {
  const violations = [];

  for (const filePath of filePaths) {
    const content = readFileSync(filePath, "utf8");
    const lines = content.split("\n");

    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      if (!line.includes("as unknown as")) continue;

      const trimmed = line.trimStart();
      if (
        trimmed.startsWith("//") ||
        trimmed.startsWith("/*") ||
        trimmed.startsWith("*")
      )
        continue;

      violations.push({
        filePath,
        line: line.trim(),
        lineNumber: i + 1,
      });
    }
  }

  return violations;
}

function formatViolations(violations) {
  return violations.map((v) => `- ${v.filePath}:${v.lineNumber}: ${v.line}`).join("\n");
}

const files = listTrackedSrcFiles();
const violations = findViolations(files);

if (violations.length > 0) {
  console.error(
    `Found 'as unknown as' casts in non-test src/** code.\n` +
      "Remove them and use boundary validation or typed adapters.\n\n" +
      formatViolations(violations)
  );
  process.exit(1);
}

process.stdout.write("OK: no 'as unknown as' casts found in src/**.\n");
