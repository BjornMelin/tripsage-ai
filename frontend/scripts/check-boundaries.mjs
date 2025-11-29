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

let violationsCount = 0;
let warningsFound = 0;

/**
 * Recursively find all TypeScript/JavaScript files in a directory.
 * Excludes test directories, test utilities, and build artifacts.
 */
function findFiles(dir, files = []) {
  const items = fs.readdirSync(dir);

  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);

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

function checkBoundaries() {
  console.log("🔍 Scanning for boundary violations...\n");

  const allFiles = [];

  for (const scanDir of SCAN_DIRS) {
    const fullScanDir = path.join(DIRNAME, "..", scanDir);
    if (fs.existsSync(fullScanDir)) {
      const files = findFiles(fullScanDir);
      allFiles.push(...files);
    }
  }

  for (const file of allFiles) {
    const content = fs.readFileSync(file, "utf8");
    const relativePath = path.relative(path.join(DIRNAME, ".."), file);

    // Check if this is a client component
    const isClientComponent =
      content.includes('"use client"') || content.includes("'use client'");

    if (isClientComponent) {
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
            console.error(`❌ BOUNDARY VIOLATION: ${relativePath}`);
            console.error(
              `   Client component imports server-only package: ${serverPackage}`
            );
            console.error(`   Matches: ${matches.join(", ")}`);
            console.error("");

            violationsCount++;
          }
        }
      }

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

  // Print summary
  console.log(`\n${"=".repeat(60)}`);
  console.log("📊 Summary");
  console.log("=".repeat(60));
  console.log(`Files scanned: ${allFiles.length}`);
  console.log(`Hard violations: ${violationsCount}`);
  console.log(`Potential issues (warnings): ${warningsFound}`);
  console.log(`${"=".repeat(60)}\n`);

  if (violationsCount > 0) {
    console.error(
      "❌ Boundary violations found! Client components should not import server-only modules."
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

try {
  checkBoundaries();
} catch (error) {
  console.error("Error scanning boundaries:", error);
  process.exit(1);
}
