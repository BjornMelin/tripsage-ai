/**
 * @fileoverview Guardrail enforcement for AI tools under src/ai/tools/server.
 *
 * Ensures server tools use createAiTool() and do not export raw tool() usages.
 * Usage: node scripts/check-ai-tools.mjs
 */

import fs from "node:fs";
import path, { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const FILENAME = fileURLToPath(import.meta.url);
const DIRNAME = dirname(FILENAME);
const REPO_ROOT = path.join(DIRNAME, "..");

const TOOL_MARKER = "ai-tool-check: allow-raw-tool";
const TOOL_ALLOWLIST = new Map([
  // TODO(ARCH-002): Legacy exceptions only. Keep this list small and burn down.
  // ["src/ai/tools/server/example.ts", "Reason + tracking ticket"],
]);

const TOOL_IMPORT_PATTERN = /import\s*{[^}]*\btool\b[^}]*}\s*from\s*["']ai["']/;
const TOOL_CALL_PATTERN = /\btool\s*\(/;

const isMainModule = (() => {
  const entry = process.argv[1];
  if (!entry) return false;
  return path.resolve(entry) === FILENAME;
})();

function stripNonCode(content) {
  let out = "";
  let state = "code";
  const stateStack = [];
  let quote = "";
  let templateExprDepth = 0;

  const pushState = (next) => {
    stateStack.push(state);
    state = next;
  };
  const popState = () => {
    state = stateStack.pop() ?? "code";
  };

  for (let i = 0; i < content.length; i += 1) {
    const ch = content[i];
    const next = content[i + 1];

    if (state === "code" || state === "template-expr") {
      if (ch === "/" && next === "/") {
        pushState("line-comment");
        out += "  ";
        i += 1;
        continue;
      }
      if (ch === "/" && next === "*") {
        pushState("block-comment");
        out += "  ";
        i += 1;
        continue;
      }
      if (ch === "'" || ch === '"') {
        quote = ch;
        pushState("string");
        out += " ";
        continue;
      }
      if (ch === "`") {
        pushState("template");
        out += " ";
        continue;
      }
      if (state === "template-expr") {
        if (ch === "{") {
          templateExprDepth += 1;
        } else if (ch === "}") {
          templateExprDepth -= 1;
          if (templateExprDepth <= 0) {
            state = "template";
            out += " ";
            continue;
          }
        }
      }
      out += ch;
      continue;
    }

    if (state === "line-comment") {
      if (ch === "\n") {
        popState();
        out += "\n";
        continue;
      }
      out += " ";
      continue;
    }

    if (state === "block-comment") {
      if (ch === "*" && next === "/") {
        popState();
        out += "  ";
        i += 1;
        continue;
      }
      out += " ";
      continue;
    }

    if (state === "string") {
      if (ch === "\\") {
        out += "  ";
        i += 1;
        continue;
      }
      if (ch === quote) {
        popState();
        out += " ";
        continue;
      }
      out += " ";
      continue;
    }

    if (state === "template") {
      if (ch === "\\") {
        out += "  ";
        i += 1;
        continue;
      }
      if (ch === "`") {
        popState();
        out += " ";
        continue;
      }
      if (ch === "$" && next === "{") {
        state = "template-expr";
        templateExprDepth = 1;
        out += "  ";
        i += 1;
        continue;
      }
      out += " ";
    }
  }

  return out;
}

function stripComments(content) {
  let out = "";
  let state = "code";
  let quote = "";

  for (let i = 0; i < content.length; i += 1) {
    const ch = content[i];
    const next = content[i + 1];

    if (state === "code") {
      if (ch === "/" && next === "/") {
        state = "line-comment";
        out += "  ";
        i += 1;
        continue;
      }
      if (ch === "/" && next === "*") {
        state = "block-comment";
        out += "  ";
        i += 1;
        continue;
      }
      if (ch === "'" || ch === '"' || ch === "`") {
        quote = ch;
        state = quote === "`" ? "template" : "string";
        out += ch;
        continue;
      }
      out += ch;
      continue;
    }

    if (state === "line-comment") {
      if (ch === "\n") {
        state = "code";
        out += "\n";
        continue;
      }
      out += " ";
      continue;
    }

    if (state === "block-comment") {
      if (ch === "*" && next === "/") {
        state = "code";
        out += "  ";
        i += 1;
        continue;
      }
      out += " ";
      continue;
    }

    if (state === "string") {
      if (ch === "\\") {
        out += ch;
        if (next) {
          out += next;
          i += 1;
        }
        continue;
      }
      out += ch;
      if (ch === quote) {
        state = "code";
      }
      continue;
    }

    if (state === "template") {
      if (ch === "\\") {
        out += ch;
        if (next) {
          out += next;
          i += 1;
        }
        continue;
      }
      out += ch;
      if (ch === "`") {
        state = "code";
      }
    }
  }

  return out;
}

function detectRawToolUsage(content) {
  const withoutComments = stripComments(content);
  const stripped = stripNonCode(content);
  return {
    hasToolCall: TOOL_CALL_PATTERN.test(stripped),
    hasToolImport: TOOL_IMPORT_PATTERN.test(withoutComments),
  };
}

function findFiles(dir, files = []) {
  let items;
  try {
    items = fs.readdirSync(dir);
  } catch (_error) {
    return files;
  }

  for (const item of items) {
    const fullPath = path.join(dir, item);
    let stat;
    try {
      stat = fs.statSync(fullPath);
    } catch (_error) {
      continue;
    }

    if (stat.isDirectory()) {
      if (
        !item.startsWith(".") &&
        item !== "node_modules" &&
        item !== "__tests__" &&
        item !== "__mocks__" &&
        item !== "test" &&
        item !== "test-utils"
      ) {
        findFiles(fullPath, files);
      }
    } else if (
      stat.isFile() &&
      (item.endsWith(".ts") || item.endsWith(".tsx")) &&
      !item.endsWith(".d.ts") &&
      !item.endsWith(".test.ts") &&
      !item.endsWith(".test.tsx") &&
      !item.endsWith(".spec.ts") &&
      !item.endsWith(".spec.tsx")
    ) {
      files.push(fullPath);
    }
  }

  return files;
}

function checkAiTools() {
  console.log("🔍 Checking AI tool guardrails...\n");

  const toolsDir = path.join(REPO_ROOT, "src/ai/tools/server");
  if (!fs.existsSync(toolsDir)) {
    console.log("✅ No server tools directory found.");
    process.exit(0);
  }

  const files = findFiles(toolsDir);
  let violations = 0;
  let allowlisted = 0;
  let warnings = 0;

  for (const file of files) {
    const relativePath = path.relative(REPO_ROOT, file);
    const normalizedPath = relativePath.split(path.sep).join("/");
    let content;
    try {
      content = fs.readFileSync(file, "utf8");
    } catch (error) {
      console.warn(
        `⚠️  Could not read file: ${normalizedPath} — ${(error instanceof Error && error.message) || error}`
      );
      warnings += 1;
      continue;
    }

    const hasMarker = content.includes(TOOL_MARKER);
    const { hasToolCall, hasToolImport } = detectRawToolUsage(content);
    const hasRawToolUsage = hasToolImport || hasToolCall;
    const allowlistReason = TOOL_ALLOWLIST.get(normalizedPath);

    if (!hasRawToolUsage) {
      if (hasMarker) {
        console.warn(`⚠️  Marker present without raw tool usage: ${normalizedPath}`);
        warnings += 1;
      }
      if (allowlistReason) {
        console.warn(`⚠️  Allowlist entry without raw tool usage: ${normalizedPath}`);
        warnings += 1;
      }
      continue;
    }

    if (allowlistReason && hasMarker) {
      console.warn(`⚠️  LEGACY ALLOWLIST: ${normalizedPath}`);
      console.warn(`   Reason: ${allowlistReason}`);
      console.warn("");
      allowlisted += 1;
      continue;
    }

    if (allowlistReason && !hasMarker) {
      console.error(`❌ ALLOWLISTED BUT UNMARKED: ${normalizedPath}`);
      console.error(`   Missing marker: // ${TOOL_MARKER}`);
      console.error("");
      violations += 1;
      continue;
    }

    if (!allowlistReason && hasMarker) {
      console.error(`❌ MARKER WITHOUT ALLOWLIST: ${normalizedPath}`);
      console.error("   Add the file to TOOL_ALLOWLIST or remove the marker.");
      console.error("");
      violations += 1;
      continue;
    }

    const issues = [];
    if (hasToolImport) issues.push('imports { tool } from "ai"');
    if (hasToolCall) issues.push("uses tool()");

    console.error(`❌ RAW TOOL USAGE: ${normalizedPath}`);
    console.error(`   ${issues.join("; ")}`);
    console.error("");
    violations += 1;
  }

  console.log(`\n${"=".repeat(60)}`);
  console.log("📊 Summary");
  console.log("=".repeat(60));
  console.log(`Files scanned: ${files.length}`);
  console.log(`Hard violations: ${violations}`);
  console.log(`Allowlisted: ${allowlisted}`);
  console.log(`Warnings: ${warnings}`);
  console.log(`${"=".repeat(60)}\n`);

  if (violations > 0) {
    console.error(
      "❌ Raw AI SDK tool() usage found in server tools. Use createAiTool()."
    );
    process.exit(1);
  }

  console.log("✅ AI tool guardrails check passed.");
  process.exit(0);
}

if (isMainModule) {
  try {
    checkAiTools();
  } catch (error) {
    console.error("Error checking AI tools:", error);
    process.exit(1);
  }
}

export { detectRawToolUsage, stripComments, stripNonCode };
