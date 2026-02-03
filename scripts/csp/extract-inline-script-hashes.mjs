/**
 * @fileoverview Extracts SHA-256 CSP hashes for inline <script> tags emitted by Next.js builds.
 *
 * Run:
 *   pnpm build
 *   node scripts/csp/extract-inline-script-hashes.mjs
 *
 * Outputs hashes for inline scripts that have no `src` and no `nonce` attribute.
 */

import crypto from "node:crypto";
import { existsSync, promises as fs } from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

function sha256Base64(value) {
  return crypto.createHash("sha256").update(value, "utf8").digest("base64");
}

async function listFilesRecursive(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const nextPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFilesRecursive(nextPath)));
      continue;
    }
    files.push(nextPath);
  }
  return files;
}

function extractInlineScriptContents(html) {
  const results = [];
  // Use a DOM parser instead of regex to handle odd script end tags like </script >.
  const dom = new JSDOM(html);
  const scripts = dom.window.document.querySelectorAll("script");
  for (const script of scripts) {
    if (script.hasAttribute("src")) continue;
    if (script.hasAttribute("nonce")) continue;
    const trimmed = script.textContent?.trim();
    if (!trimmed) continue;
    results.push(trimmed);
  }
  return results;
}

async function main() {
  const nextServerAppDir = path.join(process.cwd(), ".next", "server", "app");
  if (!existsSync(nextServerAppDir)) {
    console.error(
      `Missing ${nextServerAppDir}. Run \`pnpm build\` first to generate HTML output.`
    );
    process.exit(1);
  }

  const files = (await listFilesRecursive(nextServerAppDir)).filter((file) =>
    file.endsWith(".html")
  );

  const hashes = new Map();

  for (const file of files) {
    const html = await fs.readFile(file, "utf8");
    const scripts = extractInlineScriptContents(html);
    for (const script of scripts) {
      const hash = `'sha256-${sha256Base64(script)}'`;
      const entry = hashes.get(hash);
      if (entry) {
        entry.count += 1;
        continue;
      }
      hashes.set(hash, { count: 1, sample: file });
    }
  }

  const sorted = Array.from(hashes.entries()).sort((a, b) => a[0].localeCompare(b[0]));

  console.log("Inline <script> hashes (no src, no nonce):");
  for (const [hash, info] of sorted) {
    console.log(`${hash}  // occurrences: ${info.count}, sample: ${info.sample}`);
  }

  if (sorted.length === 0) {
    console.log("No inline scripts found in .next/server/app/**/*.html");
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
