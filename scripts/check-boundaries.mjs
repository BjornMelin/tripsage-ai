/**
 * @fileoverview Boundary violation detection script.
 * Scans for improper server-only imports in client components.
 * Usage: node scripts/check-boundaries.mjs
 *
 * Coverage:
 * - Scans all directories containing client components: src/app, src/components, src/hooks, src/stores, src/lib
 * - Excludes test files, test utilities, and build artifacts
 * - Checks for 28+ server-only packages/modules including:
 *   - Next.js server APIs (next/headers, next/cache)
 *   - Supabase server modules (@/lib/supabase/*)
 *   - Infrastructure (Redis, QStash, rate limiting, caching)
 *   - AI SDK tooling (@ai/tools, @ai/models, @ai/lib)
 *   - Domain services (@domain/accommodations/service, @domain/activities/service)
 * - Detects direct database operations and process.env usage in client components
 *
 * Whitelists (safe patterns not flagged):
 * - process.env.NODE_ENV: Compile-time constant inlined by Next.js
 * - process.env.NEXT_PUBLIC_*: Client-safe env vars inlined at build time
 * - supabase.from() with useSupabase/useSupabaseRequired: Client-side RLS-protected access
 */

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

// Server-only packages that should never be imported in client components
const SERVER_ONLY_PACKAGES = [
  "server-only",
  // Next.js server-only APIs
  "next/headers",
  "next/cache",
  // Supabase server modules
  "@/lib/supabase/server",
  "@/lib/supabase/factory",
  "@/lib/supabase/admin",
  "@/lib/supabase/rpc",
  // Environment and config
  "@/lib/env/server",
  "@/lib/auth/server",
  // Telemetry (server-only)
  "@/lib/telemetry/span",
  "@/lib/telemetry/logger",
  // Infrastructure (server-only)
  "@/lib/redis",
  "@/lib/qstash",
  "@/lib/ratelimit",
  "@/lib/cache/tags",
  "@/lib/metrics/api-metrics",
  "@/lib/embeddings/generate",
  "@/lib/memory/orchestrator",
  "@/lib/payments/stripe-client",
  "@/lib/webhooks/payload",
  "@/lib/idempotency",
  // AI SDK tooling (server-only)
  "@ai/tools",
  "@ai/tools/server",
  "@ai/models/registry",
  "@ai/lib/tool-factory",
  // Domain services (server-only)
  "@domain/accommodations/service",
  "@domain/activities/service",
];

// Directories to scan (recursive)
// Note: src/lib is included because it contains client components (error-service.ts, telemetry/client.ts, etc.)
const SCAN_DIRS = ["src/app", "src/components", "src/hooks", "src/stores", "src/lib"];

// Domain boundary enforcement (keep rules small and high-signal).
const DOMAIN_SCAN_DIR = "src/domain";
const DOMAIN_IMPORT_ALLOWLIST = new Set([
  // TODO(ARCH-001): Legacy exceptions only. Keep this list small and burn down.
  // Example: "src/domain/example/legacy.ts",
]);

// Domain schemas should remain a leaf (pure Zod definitions): they must not depend on
// Next.js/app/lib modules or `server-only` boundaries.
const DOMAIN_SCHEMAS_DIR = "src/domain/schemas";

let hardViolationsCount = 0;
let warningsFound = 0;
let allowlistedDomainViolations = 0;

/**
 * Recursively find all TypeScript/JavaScript files in a directory.
 * Excludes test directories, test utilities, and build artifacts.
 */
function findFiles(dir, files = []) {
  let items;
  try {
    items = fs.readdirSync(dir);
  } catch (_error) {
    console.warn(`⚠️  Could not read directory: ${dir}`);
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

    // Skip hidden directories, node_modules, and test-related directories
    if (stat.isDirectory()) {
      if (
        !item.startsWith(".") &&
        item !== "node_modules" &&
        item !== "__tests__" &&
        item !== "__mocks__" &&
        item !== "test" &&
        item !== "test-utils" &&
        !item.endsWith(".test") &&
        !item.endsWith(".spec")
      ) {
        findFiles(fullPath, files);
      }
    } else if (
      stat.isFile() &&
      (item.endsWith(".ts") || item.endsWith(".tsx")) &&
      !item.endsWith(".test.ts") &&
      !item.endsWith(".test.tsx") &&
      !item.endsWith(".spec.ts") &&
      !item.endsWith(".spec.tsx") &&
      item !== "test-setup.ts" &&
      item !== "vitest.config.ts"
    ) {
      files.push(fullPath);
    }
  }

  return files;
}

function getImportSpecifiers(content) {
  const specifiers = new Set();
  const patterns = [
    /(?:import|export)\s+(?:type\s+)?(?:[^'"]*?\s+from\s+)?["']([^"']+)["']/g,
    /import\(\s*["']([^"']+)["']\s*\)/g,
    /require\(\s*["']([^"']+)["']\s*\)/g,
  ];

  for (const pattern of patterns) {
    pattern.lastIndex = 0;
    let match = pattern.exec(content);
    while (match !== null) {
      if (match[1]) {
        specifiers.add(match[1]);
      }
      match = pattern.exec(content);
    }
  }

  return Array.from(specifiers);
}

function isClientComponent(content) {
  return content.includes('"use client"') || content.includes("'use client'");
}

function findDomainViolations(specifiers, filePath, repoRoot = REPO_ROOT) {
  const appViolations = [];
  const nextViolations = [];

  for (const specifier of specifiers) {
    if (specifier.startsWith("next/")) {
      nextViolations.push(specifier);
      continue;
    }

    if (specifier === "@/app" || specifier.startsWith("@/app/")) {
      appViolations.push(specifier);
      continue;
    }

    if (specifier === "src/app" || specifier.startsWith("src/app/")) {
      appViolations.push(specifier);
      continue;
    }

    if (specifier.startsWith(".")) {
      const resolved = path.resolve(path.dirname(filePath), specifier);
      if (resolved.startsWith(path.join(repoRoot, "src", "app"))) {
        appViolations.push(specifier);
      }
    }
  }

  return { appViolations, nextViolations };
}

function findDomainSchemaViolations(specifiers, filePath, repoRoot = REPO_ROOT) {
  const appViolations = [];
  const libViolations = [];
  const nextViolations = [];
  const serverOnlyViolations = [];
  const relativeEscapeViolations = [];
  const infraViolations = [];

  const schemasRoot = path.join(repoRoot, "src", "domain", "schemas");

  for (const specifier of specifiers) {
    if (specifier === "server-only") {
      serverOnlyViolations.push(specifier);
      continue;
    }

    if (specifier.startsWith("next/")) {
      nextViolations.push(specifier);
      continue;
    }

    if (specifier === "@/app" || specifier.startsWith("@/app/")) {
      appViolations.push(specifier);
      continue;
    }

    if (specifier === "src/app" || specifier.startsWith("src/app/")) {
      appViolations.push(specifier);
      continue;
    }

    if (specifier === "@/lib" || specifier.startsWith("@/lib/")) {
      libViolations.push(specifier);
      continue;
    }

    // Infrastructure aliases that domain schemas should not depend on
    // @ai/* (tools, models, registry) and @domain/*/service are server-only infrastructure
    if (
      specifier.startsWith("@ai/") ||
      (specifier.startsWith("@domain/") && specifier.includes("/service"))
    ) {
      infraViolations.push(specifier);
      continue;
    }

    if (specifier.startsWith(".")) {
      const resolved = path.resolve(path.dirname(filePath), specifier);
      if (!resolved.startsWith(schemasRoot)) {
        relativeEscapeViolations.push(specifier);
      }
    }
  }

  return {
    appViolations,
    infraViolations,
    libViolations,
    nextViolations,
    relativeEscapeViolations,
    serverOnlyViolations,
  };
}

function checkBoundaries() {
  console.log("🔍 Scanning for boundary violations...\n");

  const allFiles = [];

  for (const scanDir of SCAN_DIRS) {
    const fullScanDir = path.join(REPO_ROOT, scanDir);
    if (fs.existsSync(fullScanDir)) {
      const files = findFiles(fullScanDir);
      allFiles.push(...files);
    }
  }

  for (const file of allFiles) {
    const relativePath = path.relative(REPO_ROOT, file);
    let content;
    try {
      content = fs.readFileSync(file, "utf8");
    } catch (error) {
      console.warn(
        `⚠️  Could not read file: ${relativePath} — ${(error instanceof Error && error.message) || error}`
      );
      continue;
    }

    // Check if this is a client component
    const isClient = isClientComponent(content);

    if (isClient) {
      const packageViolations = new Set();
      // Check for server-only imports
      for (const serverPackage of SERVER_ONLY_PACKAGES) {
        // Escape special regex characters in package name
        const escapedPackage = serverPackage.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

        // Comprehensive import patterns:
        // 1. ES module: import ... from "package"
        // 2. ES module: import "package" (side-effect import)
        // 3. CommonJS: require("package")
        // 4. Dynamic import: import("package")
        const importPatterns = [
          // ES module imports with from clause
          `import\\s+.*\\s+from\\s+["']${escapedPackage}["']`,
          // ES module side-effect imports
          `import\\s+["']${escapedPackage}["']`,
          // CommonJS require
          `require\\(["']${escapedPackage}["']\\)`,
          // Dynamic import (async import())
          `import\\(["']${escapedPackage}["']\\)`,
        ];

        for (const pattern of importPatterns) {
          const regex = new RegExp(pattern, "g");
          const matches = content.match(regex);

          if (matches) {
            if (!packageViolations.has(serverPackage)) {
              console.error(`❌ BOUNDARY VIOLATION: ${relativePath}`);
              console.error(
                `   Client component imports server-only package: ${serverPackage}`
              );
              console.error(`   Matches: ${matches.join(", ")}`);
              console.error("");

              packageViolations.add(serverPackage);
            }
          }
        }
      }

      hardViolationsCount += packageViolations.size;

      // Check for direct database operations that indicate server usage
      // Use precise regex to match supabase.from() or db.from(), not Array.from()
      const dbFromPattern = /\b(supabase|db)\s*\.\s*from\s*\(/;
      if (dbFromPattern.test(content)) {
        // Whitelist: Client-side Supabase accessed via useSupabase() or useSupabaseRequired() hooks
        // These are legitimate patterns that use RLS (Row Level Security) for client-side data access
        // Detect both imports and actual hook calls
        const hasSupabaseImport =
          /import\s+.*\b(useSupabase|useSupabaseRequired)\b/.test(content);
        const hasSupabaseCall = /\b(useSupabase|useSupabaseRequired)\s*\(/.test(
          content
        );
        const usesClientSupabaseHooks = hasSupabaseImport || hasSupabaseCall;

        if (!usesClientSupabaseHooks) {
          console.error(`⚠️  POTENTIAL VIOLATION: ${relativePath}`);
          console.error(
            "   Client component contains database operations (.from() calls)"
          );
          console.error("");
          warningsFound++;
        }
        // If using client hooks, this is legitimate RLS-protected access - no warning needed
      }

      // Check for direct process.env usage (should use client-safe wrappers)
      // Whitelist: process.env.NODE_ENV (compile-time safe, inlined by Next.js)
      // Whitelist: NEXT_PUBLIC_* variables (explicitly client-safe, inlined at build time)
      const envVarPattern = /process\.env\.([A-Z0-9_]+)/g;
      let hasUnsafeEnvAccess = false;

      for (const match of content.matchAll(envVarPattern)) {
        const envVarName = match[1];
        // Skip NODE_ENV (always safe - compile-time constant)
        if (envVarName === "NODE_ENV") {
          continue;
        }
        // Skip NEXT_PUBLIC_* (explicitly client-safe)
        if (envVarName.startsWith("NEXT_PUBLIC_")) {
          continue;
        }
        // Found unsafe env var access
        hasUnsafeEnvAccess = true;
        break;
      }

      if (hasUnsafeEnvAccess) {
        console.error(`⚠️  POTENTIAL VIOLATION: ${relativePath}`);
        console.error(
          "   Client component directly accesses process.env (non-whitelisted variable)"
        );
        console.error("");
        warningsFound++;
      }
    }
  }

  // Domain layer: block imports from app/Next.js (beyond client/server boundary).
  const domainRoot = path.join(REPO_ROOT, DOMAIN_SCAN_DIR);
  if (fs.existsSync(domainRoot)) {
    const domainFiles = findFiles(domainRoot);
    for (const file of domainFiles) {
      const relativePath = path.relative(REPO_ROOT, file);
      const normalizedPath = relativePath.split(path.sep).join("/");
      let content;
      try {
        content = fs.readFileSync(file, "utf8");
      } catch (error) {
        console.warn(
          `⚠️  Could not read file: ${normalizedPath} — ${(error instanceof Error && error.message) || error}`
        );
        continue;
      }

      const specifiers = getImportSpecifiers(content);
      if (specifiers.length === 0) continue;

      if (normalizedPath.startsWith(`${DOMAIN_SCHEMAS_DIR}/`)) {
        const schemaViolations = findDomainSchemaViolations(
          specifiers,
          file,
          REPO_ROOT
        );
        const hasSchemaViolation =
          schemaViolations.appViolations.length > 0 ||
          schemaViolations.infraViolations.length > 0 ||
          schemaViolations.libViolations.length > 0 ||
          schemaViolations.nextViolations.length > 0 ||
          schemaViolations.serverOnlyViolations.length > 0 ||
          schemaViolations.relativeEscapeViolations.length > 0;

        if (hasSchemaViolation) {
          console.error(`❌ BOUNDARY VIOLATION: ${normalizedPath}`);
          if (schemaViolations.appViolations.length > 0) {
            console.error(
              `   Domain schemas import app layer: ${schemaViolations.appViolations.join(", ")}`
            );
          }
          if (schemaViolations.infraViolations.length > 0) {
            console.error(
              `   Domain schemas import infrastructure: ${schemaViolations.infraViolations.join(", ")}`
            );
          }
          if (schemaViolations.libViolations.length > 0) {
            console.error(
              `   Domain schemas import lib layer: ${schemaViolations.libViolations.join(", ")}`
            );
          }
          if (schemaViolations.nextViolations.length > 0) {
            console.error(
              `   Domain schemas import Next.js: ${schemaViolations.nextViolations.join(", ")}`
            );
          }
          if (schemaViolations.serverOnlyViolations.length > 0) {
            console.error(
              `   Domain schemas import server-only modules: ${schemaViolations.serverOnlyViolations.join(", ")}`
            );
          }
          if (schemaViolations.relativeEscapeViolations.length > 0) {
            console.error(
              `   Domain schemas import outside schemas/: ${schemaViolations.relativeEscapeViolations.join(", ")}`
            );
          }
          console.error("");
          hardViolationsCount += 1;
          continue;
        }
      }

      const { appViolations, nextViolations } = findDomainViolations(
        specifiers,
        file,
        REPO_ROOT
      );

      if (appViolations.length === 0 && nextViolations.length === 0) {
        continue;
      }

      const isAllowlisted = DOMAIN_IMPORT_ALLOWLIST.has(normalizedPath);
      const heading = isAllowlisted
        ? `⚠️  LEGACY ALLOWLIST: ${normalizedPath}`
        : `❌ BOUNDARY VIOLATION: ${normalizedPath}`;
      const log = isAllowlisted ? console.warn : console.error;

      log(heading);
      if (appViolations.length > 0) {
        log(`   Domain imports app layer: ${appViolations.join(", ")}`);
      }
      if (nextViolations.length > 0) {
        log(`   Domain imports Next.js: ${nextViolations.join(", ")}`);
      }
      log("");

      if (isAllowlisted) {
        allowlistedDomainViolations += 1;
      } else {
        hardViolationsCount += 1;
      }
    }
  }

  // Print summary
  console.log(`\n${"=".repeat(60)}`);
  console.log("📊 Summary");
  console.log("=".repeat(60));
  console.log(`Files scanned: ${allFiles.length}`);
  console.log(`Hard violations: ${hardViolationsCount}`);
  console.log(`Allowlisted domain violations: ${allowlistedDomainViolations}`);
  console.log(`Potential issues (warnings): ${warningsFound}`);
  console.log(`${"=".repeat(60)}\n`);

  if (hardViolationsCount > 0) {
    console.error(
      "❌ Boundary violations found! Check client/server and domain/app import rules."
    );
    process.exit(1);
  } else if (warningsFound > 0) {
    console.log(`⚠️  ${warningsFound} potential issue(s) found. Review warnings above.`);
    console.log("✅ No hard violations detected.");
    process.exit(0);
  } else {
    console.log("✅ No boundary violations detected.");
    process.exit(0);
  }
}

if (isMainModule) {
  try {
    checkBoundaries();
  } catch (error) {
    console.error("Error scanning boundaries:", error);
    process.exit(1);
  }
}

export { findDomainViolations, getImportSpecifiers, isClientComponent };
