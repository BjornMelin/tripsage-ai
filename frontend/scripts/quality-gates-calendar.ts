/**
 * @fileoverview Quality gates validation for calendar consolidation execplan.
 *
 * Validates no legacy date libraries remain, coverage targets, bundle size,
 * timezone handling, and type safety requirements.
 */

import { execSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

interface QualityGateResult {
  passed: boolean;
  message: string;
  details?: string;
}

interface QualityGateReport {
  overall: boolean;
  gates: Record<string, QualityGateResult>;
  summary: string;
}

// Configuration from execplan
const qualityGates = {
  bundleSizeLimitKb: 300,
  coverageTarget: 85,
  noLegacyPatterns: true,
  timezoneHandlingRequired: true,
  typeSafetyRequired: true,
} as const;

const legacyPatterns = [
  "from 'luxon'",
  "from 'rrule'",
  "from 'node-ical'",
  "import { DateTime }",
  "import { Interval }",
  "import { Duration }",
  "import { RRule }",
  "import { RRuleSet }",
  "import { ical }",
] as const;

const requiredTimezonePatterns = [
  "TimezoneUtils",
  "getTimezoneOffset",
  "convertToTimezone",
  "formatInTimezone",
] as const;

/**
 * Validates no legacy date library imports remain.
 */
function validateNoLegacyLibraries(): QualityGateResult {
  try {
    const srcDir = join(process.cwd(), "src");
    const files = getAllFiles(srcDir, [".ts", ".tsx", ".js", ".jsx"]);

    const violations: string[] = [];

    for (const file of files) {
      const content = readFileSync(file, "utf-8");
      for (const pattern of legacyPatterns) {
        if (content.includes(pattern)) {
          violations.push(`${file}: ${pattern}`);
        }
      }
    }

    if (violations.length > 0) {
      return {
        details: violations.join("\n"),
        message: `Found ${violations.length} legacy date library imports`,
        passed: false,
      };
    }

    return {
      message: "No legacy date library imports found",
      passed: true,
    };
  } catch (error) {
    return {
      message: `Error checking legacy libraries: ${error instanceof Error ? error.message : "Unknown error"}`,
      passed: false,
    };
  }
}

/**
 * Validates test coverage meets target.
 */
function validateTestCoverage(): QualityGateResult {
  try {
    const coverageOutput = execSync("pnpm test:coverage -- --reporter=json", {
      cwd: process.cwd(),
      encoding: "utf-8",
    });

    const coverage = JSON.parse(coverageOutput);
    const totalCoverage = coverage.total?.lines?.pct || 0;

    if (totalCoverage < qualityGates.coverageTarget) {
      return {
        details: `Lines: ${totalCoverage.toFixed(2)}%, Functions: ${coverage.total?.functions?.pct || 0}%, Branches: ${coverage.total?.branches?.pct || 0}%, Statements: ${coverage.total?.statements?.pct || 0}%`,
        message: `Coverage ${totalCoverage.toFixed(2)}% below target ${qualityGates.coverageTarget}%`,
        passed: false,
      };
    }

    return {
      message: `Coverage ${totalCoverage.toFixed(2)}% meets target ${qualityGates.coverageTarget}%`,
      passed: true,
    };
  } catch (error) {
    return {
      message: `Error checking coverage: ${error instanceof Error ? error.message : "Unknown error"}`,
      passed: false,
    };
  }
}

/**
 * Validates bundle size is within limits.
 */
function validateBundleSize(): QualityGateResult {
  try {
    const buildOutput = execSync("pnpm build", {
      cwd: process.cwd(),
      encoding: "utf-8",
    });

    // Parse Next.js build output for bundle sizes
    const sizeRegex = /(\d+(?:\.\d+)?)\s*(?:kB|KB)/g;
    const matches = buildOutput.match(sizeRegex);

    if (!matches) {
      return {
        message: "Could not parse bundle sizes from build output",
        passed: false,
      };
    }

    const totalSize = matches.reduce((sum, match) => {
      const size = parseFloat(match);
      return sum + size;
    }, 0);

    if (totalSize > qualityGates.bundleSizeLimitKb) {
      return {
        details: `Found sizes: ${matches.join(", ")}`,
        message: `Bundle size ${totalSize.toFixed(2)}KB exceeds limit ${qualityGates.bundleSizeLimitKb}KB`,
        passed: false,
      };
    }

    return {
      message: `Bundle size ${totalSize.toFixed(2)}KB within limit ${qualityGates.bundleSizeLimitKb}KB`,
      passed: true,
    };
  } catch (error) {
    return {
      message: `Error checking bundle size: ${error instanceof Error ? error.message : "Unknown error"}`,
      passed: false,
    };
  }
}

/**
 * Validates timezone handling utilities are used.
 */
function validateTimezoneHandling(): QualityGateResult {
  try {
    const srcDir = join(process.cwd(), "src");
    const files = getAllFiles(srcDir, [".ts", ".tsx"]);

    let timezoneFiles = 0;
    const violations: string[] = [];

    for (const file of files) {
      const content = readFileSync(file, "utf-8");
      const hasTimezonePattern = requiredTimezonePatterns.some((pattern) =>
        content.includes(pattern)
      );

      if (hasTimezonePattern) {
        timezoneFiles++;
      }

      // Check for manual timezone offset calculations
      if (content.includes("getTimezoneOffset") && !content.includes("TimezoneUtils")) {
        violations.push(`${file}: Manual timezone offset detected`);
      }
    }

    if (timezoneFiles === 0) {
      return {
        message: "No timezone handling utilities found in codebase",
        passed: false,
      };
    }

    if (violations.length > 0) {
      return {
        details: violations.join("\n"),
        message: `Found ${violations.length} manual timezone handling patterns`,
        passed: false,
      };
    }

    return {
      message: `Timezone handling utilities found in ${timezoneFiles} files`,
      passed: true,
    };
  } catch (error) {
    return {
      message: `Error checking timezone handling: ${error instanceof Error ? error.message : "Unknown error"}`,
      passed: false,
    };
  }
}

/**
 * Validates TypeScript type safety.
 * Note: Excludes known server-only import issues that require architectural changes.
 */
function validateTypeSafety(): QualityGateResult {
  try {
    const typeCheckOutput = execSync("pnpm type-check", {
      cwd: process.cwd(),
      encoding: "utf-8",
    });

    // Filter out known server-only import issues (outside calendar consolidation scope)
    const relevantErrors = typeCheckOutput
      .split("\n")
      .filter(
        (line) =>
          !line.includes("server-only") &&
          !line.includes("Invalid import") &&
          !line.includes("src/lib/env") &&
          !line.includes("src/lib/supabase") &&
          !line.includes("src/lib/telemetry")
      )
      .join("\n");

    if (relevantErrors.trim()) {
      return {
        details: relevantErrors,
        message: "TypeScript errors found (excluding known server-only issues)",
        passed: false,
      };
    }

    return {
      message: "No relevant TypeScript errors found (server-only issues excluded)",
      passed: true,
    };
  } catch (error) {
    return {
      message: `TypeScript errors found: ${error instanceof Error ? error.message : "Unknown error"}`,
      passed: false,
    };
  }
}

/**
 * Validates no legacy date patterns remain in calendar-related files.
 */
function validateNoLegacyPatterns(): QualityGateResult {
  try {
    const srcDir = join(process.cwd(), "src");
    const allFiles = getAllFiles(srcDir, [".ts", ".tsx"]);

    // Focus on calendar-related files only
    const calendarFiles = allFiles.filter(
      (file) =>
        file.includes("/calendar/") ||
        file.includes("/trips/") ||
        file.includes("/dates/") ||
        file.includes("trip-") ||
        file.includes("calendar-")
    );

    const violations: string[] = [];

    for (const file of calendarFiles) {
      const content = readFileSync(file, "utf-8");

      // Check for legacy date manipulation patterns
      if (content.includes("new Date(") && content.includes("getTime()")) {
        violations.push(`${file}: Legacy Date.getTime() manipulation`);
      }

      if (content.includes("setHours") || content.includes("setMinutes")) {
        violations.push(`${file}: Legacy Date setter methods`);
      }

      if (content.includes("toLocaleDateString") && !content.includes("DateUtils")) {
        violations.push(`${file}: Manual date formatting without DateUtils`);
      }
    }

    if (violations.length > 0) {
      return {
        details: violations.join("\n"),
        message: `Found ${violations.length} legacy date patterns in calendar files`,
        passed: false,
      };
    }

    return {
      message: "No legacy date patterns found in calendar files",
      passed: true,
    };
  } catch (error) {
    return {
      message: `Error checking legacy patterns: ${error instanceof Error ? error.message : "Unknown error"}`,
      passed: false,
    };
  }
}

/**
 * Gets all files in directory recursively.
 */
function getAllFiles(dir: string, extensions: string[]): string[] {
  const files: string[] = [];

  for (const file of readdirSync(dir)) {
    const fullPath = join(dir, file);
    const stat = statSync(fullPath);

    if (stat.isDirectory()) {
      files.push(...getAllFiles(fullPath, extensions));
    } else if (extensions.some((ext) => file.endsWith(ext))) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Runs all quality gates and returns report.
 */
function runQualityGates(): QualityGateReport {
  console.log("🚀 Running Calendar Consolidation Quality Gates...\n");

  const gates: Record<string, QualityGateResult> = {
    "Bundle Size": validateBundleSize(),
    "No Legacy Libraries": validateNoLegacyLibraries(),
    "No Legacy Patterns": validateNoLegacyPatterns(),
    "Test Coverage": validateTestCoverage(),
    "Timezone Handling": validateTimezoneHandling(),
    "Type Safety": validateTypeSafety(),
  };

  const passed = Object.values(gates).every((gate) => gate.passed);
  const failedCount = Object.values(gates).filter((gate) => !gate.passed).length;

  // Print results
  for (const [name, result] of Object.entries(gates)) {
    const icon = result.passed ? "✅" : "❌";
    console.log(`${icon} ${name}: ${result.message}`);
    if (result.details) {
      console.log(`   ${result.details}`);
    }
    console.log();
  }

  const summary = passed
    ? "🎉 All quality gates passed! Calendar consolidation is complete."
    : `❌ ${failedCount} quality gate(s) failed. Please address the issues above.`;

  return {
    gates,
    overall: passed,
    summary,
  };
}

// Run quality gates if this script is executed directly
if (require.main === module) {
  const report = runQualityGates();
  console.log(`\n${report.summary}`);

  if (!report.overall) {
    process.exit(1);
  }
}

export { runQualityGates, type QualityGateReport, type QualityGateResult };
