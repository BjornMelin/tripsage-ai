#!/usr/bin/env node

/**
 * @fileoverview Validates active Markdown relative links and heading anchors.
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const REPO_ROOT = process.cwd();
const DEFAULT_TARGETS = ["README.md", "docs"];
const EXCLUDED_PARTS = new Set(["archive", "reviews"]);
const EXCLUDED_PREFIXES = [
  "docs/development/frontend/frontend-readme-archive.md",
  "docs/plans/archive/",
  "docs/specs/archive/",
  "docs/architecture/decisions/superseded/",
];

function toPosix(filePath) {
  return filePath.split(path.sep).join("/");
}

function isExcluded(filePath) {
  const relative = toPosix(path.relative(REPO_ROOT, filePath));
  if (EXCLUDED_PREFIXES.some((prefix) => relative.startsWith(prefix))) return true;
  return relative.split("/").some((part) => EXCLUDED_PARTS.has(part));
}

function collectMarkdownFiles(targets) {
  const files = [];

  function visit(entryPath) {
    if (!fs.existsSync(entryPath) || isExcluded(entryPath)) return;
    const stat = fs.statSync(entryPath);
    if (stat.isDirectory()) {
      for (const child of fs.readdirSync(entryPath)) visit(path.join(entryPath, child));
      return;
    }
    if (entryPath.endsWith(".md")) files.push(entryPath);
  }

  for (const target of targets) visit(path.resolve(REPO_ROOT, target));
  return files.sort();
}

function stripCodeFences(markdown) {
  return markdown.replace(/```[\s\S]*?```/gu, "").replace(/~~~[\s\S]*?~~~/gu, "");
}

function extractMarkdownLinks(markdown) {
  const links = [];
  const withoutCode = stripCodeFences(markdown);
  const inlineLinkPattern = /(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+"[^"]*")?\)/gu;
  const referenceDefinitionPattern = /^\[[^\]]+\]:\s+(\S+)/gmu;

  for (const match of withoutCode.matchAll(inlineLinkPattern)) links.push(match[1]);
  for (const match of withoutCode.matchAll(referenceDefinitionPattern))
    links.push(match[1]);
  return links;
}

function isSkippableLink(link) {
  return (
    link.startsWith("http://") ||
    link.startsWith("https://") ||
    link.startsWith("mailto:") ||
    link.startsWith("tel:") ||
    link.startsWith("app://")
  );
}

function normalizeTarget(rawLink) {
  const unwrapped = rawLink.replace(/^<|>$/gu, "");
  const [withoutQuery] = unwrapped.split("?");
  const [filePart, anchor = ""] = withoutQuery.split("#");
  return { anchor, filePart };
}

function headingToAnchor(heading) {
  return heading
    .trim()
    .toLowerCase()
    .replace(/`([^`]+)`/gu, "$1")
    .replace(/[<>]/gu, "")
    .replace(/[^\p{Letter}\p{Number}\s_-]/gu, "")
    .trim()
    .replace(/\s/gu, "-");
}

function collectAnchors(filePath) {
  const markdown = stripCodeFences(fs.readFileSync(filePath, "utf8"));
  const anchors = new Set();
  const headingPattern = /^#{1,6}\s+(.+)$/gmu;
  const explicitIdPattern = /\{#([^}]+)\}/gu;

  for (const match of markdown.matchAll(headingPattern)) {
    anchors.add(headingToAnchor(match[1].replace(/\s+\{#[^}]+\}\s*$/u, "")));
  }
  for (const match of markdown.matchAll(explicitIdPattern)) anchors.add(match[1]);

  return anchors;
}

function resolveLinkedFile(sourceFile, filePart) {
  const base = filePart ? path.resolve(path.dirname(sourceFile), filePart) : sourceFile;
  if (fs.existsSync(base)) {
    const stat = fs.statSync(base);
    if (stat.isDirectory()) {
      for (const indexName of ["README.md", "index.md"]) {
        const indexPath = path.join(base, indexName);
        if (fs.existsSync(indexPath)) return indexPath;
      }
      return base;
    }
    return base;
  }

  if (!path.extname(base)) {
    const markdownPath = `${base}.md`;
    if (fs.existsSync(markdownPath)) return markdownPath;
  }

  return null;
}

function main() {
  const targets = process.argv.slice(2);
  const files = collectMarkdownFiles(targets.length > 0 ? targets : DEFAULT_TARGETS);
  const anchorCache = new Map();
  const failures = [];

  for (const file of files) {
    const markdown = fs.readFileSync(file, "utf8");
    for (const rawLink of extractMarkdownLinks(markdown)) {
      if (isSkippableLink(rawLink)) continue;
      const { anchor, filePart } = normalizeTarget(rawLink);
      if (!filePart && !anchor) continue;

      const linkedFile = resolveLinkedFile(file, filePart);
      if (!linkedFile) {
        failures.push(`${toPosix(path.relative(REPO_ROOT, file))}: missing ${rawLink}`);
        continue;
      }

      if (!anchor || !linkedFile.endsWith(".md")) continue;

      let anchors = anchorCache.get(linkedFile);
      if (!anchors) {
        anchors = collectAnchors(linkedFile);
        anchorCache.set(linkedFile, anchors);
      }
      if (!anchors.has(decodeURIComponent(anchor).toLowerCase())) {
        failures.push(
          `${toPosix(path.relative(REPO_ROOT, file))}: missing anchor ${rawLink}`
        );
      }
    }
  }

  if (failures.length > 0) {
    console.error(`Found ${failures.length} broken active doc link(s):`);
    for (const failure of failures) console.error(`- ${failure}`);
    process.exit(1);
  }

  console.log(`Checked ${files.length} active Markdown file(s).`);
}

main();
