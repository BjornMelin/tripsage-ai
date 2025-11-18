/**
 * @fileoverview Boundary violation detection script.
 * Scans for improper server-only imports in client components.
 * Usage: node scripts/check-boundaries.js
 */

const fs = require("node:fs");
const path = require("node:path");

// Server-only packages that should never be imported in client components
const SERVER_ONLY_PACKAGES = [
  "server-only",
  "@/lib/supabase/server",
  "@/lib/supabase/factory",
  "next/headers",
  "next/cache",
];

// Directories to scan (recursive)
const SCAN_DIRS = ["src/app", "src/components", "src/hooks", "src/stores"];

let violationsFound = false;

/**
 * Recursively find all TypeScript/JavaScript files in a directory
 */
function findFiles(dir, files = []) {
  const items = fs.readdirSync(dir);

  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory() && !item.startsWith(".") && item !== "node_modules") {
      findFiles(fullPath, files);
    } else if (stat.isFile() && (item.endsWith(".ts") || item.endsWith(".tsx"))) {
      files.push(fullPath);
    }
  }

  return files;
}

function checkBoundaries() {
  console.log("🔍 Scanning for boundary violations...\n");

  const allFiles = [];

  for (const scanDir of SCAN_DIRS) {
    const fullScanDir = path.join(__dirname, "..", scanDir);
    if (fs.existsSync(fullScanDir)) {
      const files = findFiles(fullScanDir);
      allFiles.push(...files);
    }
  }

  for (const file of allFiles) {
    const content = fs.readFileSync(file, "utf8");
    const relativePath = path.relative(path.join(__dirname, ".."), file);

    // Check if this is a client component
    const isClientComponent =
      content.includes('"use client"') || content.includes("'use client'");

    if (isClientComponent) {
      // Check for server-only imports
      for (const serverPackage of SERVER_ONLY_PACKAGES) {
        const importPatterns = [
          `from "${serverPackage}"`,
          `from '${serverPackage}'`,
          `import.*"${serverPackage}"`,
          `import.*'${serverPackage}'`,
          `require\\("${serverPackage}"\\)`,
          `require\\('${serverPackage}'\\)`,
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

            violationsFound = true;
          }
        }
      }

      // Check for direct database operations that indicate server usage
      if (
        content.includes(".from(") &&
        (content.includes("supabase") || content.includes("db"))
      ) {
        console.error(`⚠️  POTENTIAL VIOLATION: ${relativePath}`);
        console.error(
          "   Client component contains database operations (.from() calls)"
        );
        console.error("");
      }

      // Check for direct process.env usage (should use client-safe wrappers)
      if (content.includes("process.env.")) {
        console.error(`⚠️  POTENTIAL VIOLATION: ${relativePath}`);
        console.error("   Client component directly accesses process.env");
        console.error("");
      }
    }
  }

  if (violationsFound) {
    console.error(
      "❌ Boundary violations found! Client components should not import server-only modules."
    );
    process.exit(1);
  } else {
    console.log("✅ No boundary violations detected.");
  }
}

try {
  checkBoundaries();
} catch (error) {
  console.error("Error scanning boundaries:", error);
  process.exit(1);
}
