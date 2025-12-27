/**
 * @fileoverview AI SDK version contract check.
 *
 * Ensures:
 * - `AGENTS.md` mirrors the AI SDK package versions pinned in `package.json`
 * - Docs do not reference AI SDK beta pins (e.g. `ai@6.0.0-beta.123`)
 *
 * Usage: node scripts/check-ai-sdk-version-contract.mjs
 */

import { execSync } from "node:child_process";
import fs from "node:fs";
import path, { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const FILENAME = fileURLToPath(import.meta.url);
const DIRNAME = dirname(FILENAME);
const REPO_ROOT = path.join(DIRNAME, "..");

const isMainModule = (() => {
  const entry = process.argv[1];
  if (!entry) return false;
  return path.resolve(entry) === FILENAME;
})();

const AI_SDK_PACKAGES = [
  "ai",
  "@ai-sdk/react",
  "@ai-sdk/openai",
  "@ai-sdk/anthropic",
  "@ai-sdk/xai",
  "@ai-sdk/togetherai",
];

const FORBIDDEN_PATTERNS = [
  {
    id: "ai-sdk-beta-pin",
    label: "AI SDK beta pin (ai@x.y.z-beta.n)",
    regex: /\bai@\d+\.\d+\.\d+-beta\.\d+\b/g,
  },
  {
    id: "ai-sdk-provider-beta-pin",
    label: "AI SDK provider beta pin (@ai-sdk/*@x.y.z-beta.n)",
    regex: /\b@ai-sdk\/[a-z-]+@\d+\.\d+\.\d+-beta\.\d+\b/g,
  },
  {
    id: "ai-sdk-v6-beta-badge",
    label: "AI SDK v6_beta badge string",
    regex: /AI_SDK-v6_beta/g,
  },
];

function readTextFileOrExit(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (error) {
    console.error(
      `❌ Failed to read file: ${filePath} — ${(error instanceof Error && error.message) || error}`
    );
    process.exit(1);
  }
}

function readJsonFileOrExit(filePath) {
  const raw = readTextFileOrExit(filePath);
  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error(
      `❌ Failed to parse JSON: ${filePath} — ${(error instanceof Error && error.message) || error}`
    );
    process.exit(1);
  }
}

function listTrackedMarkdownFiles() {
  let stdout = "";
  try {
    stdout = execSync("git ls-files docs README.md", {
      cwd: REPO_ROOT,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    console.error(
      `❌ Failed to list tracked files via git — ${(error instanceof Error && error.message) || error}`
    );
    process.exit(1);
  }

  const files = stdout
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && line.endsWith(".md"))
    .map((file) => path.join(REPO_ROOT, file));

  return files.filter((file) => fs.existsSync(file));
}

function indexToLineNumber(content, index) {
  return content.slice(0, index).split("\n").length;
}

function checkAgentsContract({ agentsText, expectedVersions }) {
  const failures = [];

  for (const [pkg, version] of expectedVersions.entries()) {
    const token = `${pkg}@${version}`;
    if (!agentsText.includes(token)) {
      failures.push(`Missing in AGENTS.md: \`${token}\``);
    }
  }

  if (failures.length > 0) {
    console.error(
      "❌ AI SDK version contract mismatch between package.json and AGENTS.md."
    );
    for (const failure of failures) console.error(`   - ${failure}`);
    process.exit(1);
  }
}

function checkDocsForForbiddenPins({ markdownFiles }) {
  const violations = [];

  for (const filePath of markdownFiles) {
    const content = readTextFileOrExit(filePath);
    for (const { id, label, regex } of FORBIDDEN_PATTERNS) {
      regex.lastIndex = 0;
      let match;
      match = regex.exec(content);
      while (match !== null) {
        const line = indexToLineNumber(content, match.index);
        violations.push({
          filePath,
          id,
          label,
          line,
          match: match[0],
        });
        match = regex.exec(content);
      }
    }
  }

  if (violations.length > 0) {
    console.error("❌ Forbidden AI SDK references found in docs.");
    for (const violation of violations) {
      const relative = path
        .relative(REPO_ROOT, violation.filePath)
        .split(path.sep)
        .join("/");
      console.error(
        `   - ${relative}:${violation.line} — ${violation.label} — "${violation.match}"`
      );
    }
    process.exit(1);
  }
}

function main() {
  const pkgJson = readJsonFileOrExit(path.join(REPO_ROOT, "package.json"));
  const agentsText = readTextFileOrExit(path.join(REPO_ROOT, "AGENTS.md"));

  const deps = pkgJson.dependencies ?? {};
  const expectedVersions = new Map();

  for (const pkg of AI_SDK_PACKAGES) {
    const version = deps[pkg];
    if (typeof version !== "string") {
      console.error(`❌ Missing dependency in package.json: ${pkg}`);
      process.exit(1);
    }
    if (/^[~^]/.test(version)) {
      console.error(
        `❌ AI SDK dependencies must be pinned to exact versions: ${pkg}@${version}`
      );
      process.exit(1);
    }
    expectedVersions.set(pkg, version);
  }

  checkAgentsContract({ agentsText, expectedVersions });

  const markdownFiles = listTrackedMarkdownFiles();

  checkDocsForForbiddenPins({ markdownFiles });

  console.log("✅ AI SDK version contract verified.");
}

if (isMainModule) {
  main();
}
