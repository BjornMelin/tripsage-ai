/**
 * @fileoverview Diff-based secret scanner for preventing committed credentials.
 *
 * This is intentionally high-signal (low false positives) and dependency-free.
 * It scans changed tracked files by default, and supports `--full` to scan all tracked files.
 *
 * Output redacts matched values to avoid leaking secrets in CI logs.
 */

import { execFileSync } from "node:child_process";
import { readFileSync, statSync } from "node:fs";

const ARGS = new Set(process.argv.slice(2));
const MODE = ARGS.has("--full") ? "full" : ARGS.has("--staged") ? "staged" : "diff";

const MAX_FILE_BYTES = 1_000_000; // 1MB

const TEXT_FILE_RE =
  /\.(c|m)?[tj]sx?$|\.json$|\.sql$|\.ya?ml$|\.md$|\.txt$|\.env(\..*)?$/;
const EXCLUDED_PATH_PARTS = [
  "node_modules/",
  ".next/",
  "coverage/",
  ".vitest/",
  ".git/",
];
const ENV_FILE_RE = /(^|\/)\.env(\..*)?$/;
const TRACKED_ENV_ALLOW_RE = /\.(?:example|sample|template)$/;

function isExcludedPath(filePath) {
  if (EXCLUDED_PATH_PARTS.some((part) => filePath.includes(part))) return true;
  return !TEXT_FILE_RE.test(filePath);
}

function redactValue(value) {
  const text = String(value);
  if (text.length <= 12) return "[REDACTED]";
  return `${text.slice(0, 6)}…${text.slice(-4)}`;
}

function runGitDiffNameOnly(range) {
  return execFileSync("git", ["diff", "--name-only", range], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function getStagedFiles() {
  const out = execFileSync("git", ["diff", "--cached", "--name-only"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return out
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function getChangedFiles() {
  const candidates = ["origin/main...HEAD", "main...HEAD"];
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

function getTrackedFiles() {
  const out = execFileSync("git", ["ls-files"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return out
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function assertNoTrackedEnvFiles() {
  const tracked = getTrackedFiles();
  const disallowed = tracked
    .filter((filePath) => ENV_FILE_RE.test(filePath))
    .filter((filePath) => !TRACKED_ENV_ALLOW_RE.test(filePath));
  if (disallowed.length === 0) return;

  process.stderr.write(
    "Tracked .env files detected. Do not commit environment files; use .env.example instead.\n\n"
  );
  for (const filePath of disallowed) {
    process.stderr.write(`- ${filePath}\n`);
  }
  process.exit(1);
}

const TOKEN_PATTERNS = [
  {
    id: "pem_private_key",
    regex: /-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----/g,
  },
  { id: "stripe_secret_key", regex: /\bsk_(?:live|test)_[0-9a-zA-Z]{20,}\b/g },
  { id: "stripe_webhook_secret", regex: /\bwhsec_[0-9a-zA-Z]{20,}\b/g },
  { id: "github_token", regex: /\bghp_[0-9A-Za-z]{36,}\b/g },
  { id: "github_pat", regex: /\bgithub_pat_[0-9A-Za-z_]{40,}\b/g },
  { id: "slack_token", regex: /\bxox[baprs]-[0-9A-Za-z-]{20,}\b/g },
  { id: "anthropic_api_key", regex: /\bsk-ant-[0-9A-Za-z_-]{20,}\b/g },
  { id: "openrouter_api_key", regex: /\bsk-or-v1-[0-9A-Za-z_-]{20,}\b/g },
  // OpenAI-style keys are longer in practice; use a higher floor to reduce false positives.
  { id: "openai_like_key", regex: /\bsk-[0-9A-Za-z]{40,}\b/g },
  { id: "resend_api_key", regex: /\bre_[0-9A-Za-z]{20,}\b/g },
  { id: "aws_access_key_id", regex: /\bAKIA[0-9A-Z]{16}\b/g },
  { id: "google_api_key", regex: /\bAIza[0-9A-Za-z-_]{35}\b/g },
  { id: "vercel_token", regex: /\bvercel_[0-9A-Za-z]{20,}\b/g },
];

const ENV_ASSIGNMENT_NAMES = [
  "AI_GATEWAY_API_KEY",
  "AMADEUS_CLIENT_SECRET",
  "ANTHROPIC_API_KEY",
  "BYOK_HEALTHCHECK_KEY",
  "DATABASE_URL",
  "DUFFEL_ACCESS_TOKEN",
  "DUFFEL_API_KEY",
  "EMBEDDINGS_API_KEY",
  "FIRECRAWL_API_KEY",
  "GOOGLE_MAPS_SERVER_API_KEY",
  "HMAC_SECRET",
  "MFA_BACKUP_CODE_PEPPER",
  "OPENAI_API_KEY",
  "OPENROUTER_API_KEY",
  "OPENWEATHERMAP_API_KEY",
  "QSTASH_TOKEN",
  "QSTASH_CURRENT_SIGNING_KEY",
  "QSTASH_NEXT_SIGNING_KEY",
  "RESEND_API_KEY",
  "STRIPE_SECRET_KEY",
  "STRIPE_WEBHOOK_SECRET",
  "SUPABASE_JWT_SECRET",
  "SUPABASE_SERVICE_ROLE_KEY",
  "TELEMETRY_HASH_SECRET",
  "TELEMETRY_AI_DEMO_KEY",
  "TOGETHER_AI_API_KEY",
  "TOGETHER_API_KEY",
  "UPSTASH_REDIS_REST_TOKEN",
  "UPSTASH_REDIS_REST_URL",
  "XAI_API_KEY",
];

function isObviousPlaceholder(value) {
  const v = String(value).trim();
  if (!v) return true;

  const lowered = v.toLowerCase();
  const markers = [
    "example",
    "changeme",
    "replace_me",
    "your-",
    "your_",
    "dummysignature",
    "dummy",
    "mock",
    "placeholder",
    "postgres:postgres@127.0.0.1",
    "postgres:postgres@localhost",
  ];
  if (markers.some((m) => lowered.includes(m))) return true;

  // Repeated single character strings are commonly used as non-secret stubs in CI/test.
  if (/^([a-zA-Z0-9])\1{15,}$/.test(v)) return true;

  return false;
}

function findEnvAssignments(text, filePath) {
  const findings = [];
  const shouldScanUnquotedEnvAssignments = ENV_FILE_RE.test(filePath);

  for (const name of ENV_ASSIGNMENT_NAMES) {
    const re = new RegExp(
      String.raw`\b${name}\b[ \t]*[:=][ \t]*(['\"])([^'\"\r\n]+)\1`,
      "g"
    );
    for (const match of text.matchAll(re)) {
      const value = match[2] ?? "";
      if (isObviousPlaceholder(value)) continue;
      if (value.length < 12) continue;
      findings.push({
        id: "env_assignment",
        kind: name,
        redacted: redactValue(value),
      });
    }

    if (!shouldScanUnquotedEnvAssignments) continue;

    const unquotedRe = new RegExp(
      String.raw`(?:^|\n)[ \t]*(?:export[ \t]+)?${name}[ \t]*=[ \t]*([^#\r\n]+)`,
      "g"
    );
    for (const match of text.matchAll(unquotedRe)) {
      const value = (match[1] ?? "").trim();
      if (isObviousPlaceholder(value)) continue;
      if (value.length < 12) continue;
      findings.push({
        id: "env_assignment",
        kind: name,
        redacted: redactValue(value),
      });
    }
  }
  return findings;
}

function findTokenMatches(text) {
  const findings = [];
  for (const pattern of TOKEN_PATTERNS) {
    for (const match of text.matchAll(pattern.regex)) {
      const value = match[0] ?? "";
      findings.push({
        id: pattern.id,
        kind: pattern.id,
        redacted:
          pattern.id === "pem_private_key" ? "[PRIVATE KEY]" : redactValue(value),
      });
    }
  }
  return findings;
}

function readTextIfSmall(filePath) {
  const st = statSync(filePath);
  if (!st.isFile()) return null;
  if (st.size > MAX_FILE_BYTES) return null;
  return readFileSync(filePath, "utf8");
}

assertNoTrackedEnvFiles();

const candidateFiles =
  MODE === "full"
    ? getTrackedFiles()
    : MODE === "staged"
      ? getStagedFiles()
      : getChangedFiles();
const filesToScan = candidateFiles.filter((filePath) => !isExcludedPath(filePath));

const violations = [];

for (const filePath of filesToScan) {
  let text;
  try {
    text = readTextIfSmall(filePath);
  } catch {
    continue;
  }
  if (!text) continue;

  const matches = [...findTokenMatches(text), ...findEnvAssignments(text, filePath)];
  if (matches.length === 0) continue;

  violations.push({
    filePath,
    matches,
  });
}

if (violations.length > 0) {
  process.stderr.write(
    `Potential secrets detected in ${
      MODE === "full" ? "tracked" : MODE === "staged" ? "staged" : "changed"
    } files.\n` +
      "Remove secrets from the repo and move them to env vars/secret manager.\n\n"
  );

  for (const v of violations) {
    process.stderr.write(`- ${v.filePath}\n`);
    for (const m of v.matches) {
      process.stderr.write(`  - ${m.kind}: ${m.redacted}\n`);
    }
  }
  process.exit(1);
}

process.stdout.write(
  `OK: no secrets detected in ${
    MODE === "full" ? "tracked" : MODE === "staged" ? "staged" : "changed"
  } files.\n`
);
