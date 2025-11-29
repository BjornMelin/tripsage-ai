#!/usr/bin/env tsx

/**
 * @fileoverview Test performance benchmark script for Vitest.
 * Collects test durations per file, calculates percentiles, and validates thresholds.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import process from "node:process";

/**
 * Test file performance metrics.
 */
interface TestFileMetrics {
  duration: number;
  failed: number;
  name: string;
  passed: number;
  tests: number;
}

/**
 * Benchmark results summary.
 */
interface BenchmarkResults {
  files: TestFileMetrics[];
  percentiles: {
    p50: number;
    p90: number;
    p95: number;
  };
  suite: {
    duration: number;
    failed: number;
    passed: number;
    tests: number;
  };
  thresholds: {
    exceeded: string[];
    fileFailThreshold: number;
    fileWarningThreshold: number;
    suiteThreshold: number;
    suitePassed: boolean;
    warnings: string[];
  };
}

/**
 * Vitest JSON report structure.
 */
interface VitestJsonReport {
  numFailedTests: number;
  numPassedTests: number;
  numTotalTests: number;
  startTime: number;
  testResults: Array<{
    assertionResults: Array<{
      duration: number;
      status: string;
    }>;
    endTime: number;
    name: string;
    startTime: number;
  }>;
}

/**
 * Calculate percentile from sorted array.
 */
function calculatePercentile(sorted: number[], percentile: number): number {
  if (sorted.length === 0) return 0;
  const index = Math.ceil((percentile / 100) * sorted.length) - 1;
  return sorted[Math.max(0, Math.min(index, sorted.length - 1))];
}

/**
 * Parse Vitest JSON output and extract metrics.
 */
function parseVitestJson(jsonPath: string): BenchmarkResults {
  if (!existsSync(jsonPath)) {
    throw new Error(`Vitest JSON report not found: ${jsonPath}`);
  }

  let report: VitestJsonReport;
  try {
    report = JSON.parse(readFileSync(jsonPath, "utf-8"));
  } catch (error) {
    throw new Error(
      `Failed to parse Vitest JSON report (${jsonPath}): ${error instanceof Error ? error.message : String(error)}`
    );
  }

  // Validate required fields
  if (!Array.isArray(report.testResults)) {
    throw new Error(`Invalid Vitest report: testResults is not an array (${jsonPath})`);
  }
  if (typeof report.startTime !== "number") {
    console.warn(
      `Warning: Vitest report startTime is not a number (${jsonPath}), using fallback calculation`
    );
  }

  const files: TestFileMetrics[] = report.testResults.map((result) => {
    const duration =
      typeof result.endTime === "number" && typeof result.startTime === "number"
        ? result.endTime - result.startTime
        : result.assertionResults.reduce(
            (sum, assertion) => sum + (assertion.duration ?? 0),
            0
          );
    const passed = result.assertionResults.filter((r) => r.status === "passed").length;
    const failed = result.assertionResults.filter((r) => r.status === "failed").length;

    return {
      duration,
      failed,
      name: result.name,
      passed,
      tests: passed + failed,
    };
  });

  const durations = files.map((f) => f.duration).sort((a, b) => a - b);

  // Prefer wall-clock duration when start/end timestamps are present; otherwise
  // fall back to the max file duration (parallel execution semantics)
  const suiteDuration = (() => {
    const endTimes = report.testResults
      .map((r) => r.endTime)
      .filter((v): v is number => typeof v === "number");
    if (endTimes.length > 0 && typeof report.startTime === "number") {
      return Math.max(...endTimes) - report.startTime;
    }
    // Fallback: use max duration (parallel execution semantics) instead of sum
    const fileDurations = files.map((f) => f.duration).filter((d) => d > 0);
    return fileDurations.length > 0 ? Math.max(...fileDurations) : 0;
  })();

  const percentiles = {
    p50: calculatePercentile(durations, 50),
    p90: calculatePercentile(durations, 90),
    p95: calculatePercentile(durations, 95),
  };

  // Thresholds configurable via environment variables with validation
  // biome-ignore lint/style/useNamingConvention: SCREAMING_SNAKE for immutable defaults
  const SUITE_DEFAULT = 20000;
  // biome-ignore lint/style/useNamingConvention: SCREAMING_SNAKE for immutable defaults
  const FILE_WARNING_DEFAULT = 500;
  // biome-ignore lint/style/useNamingConvention: SCREAMING_SNAKE for immutable defaults
  const FILE_FAIL_DEFAULT = 3500;

  const parsedSuite = Number(process.env.BENCHMARK_SUITE_THRESHOLD_MS);
  const suiteThreshold =
    !Number.isNaN(parsedSuite) && parsedSuite > 0 ? parsedSuite : SUITE_DEFAULT;

  const parsedWarning = Number(process.env.BENCHMARK_FILE_WARNING_MS);
  const fileWarningThreshold =
    !Number.isNaN(parsedWarning) && parsedWarning > 0
      ? parsedWarning
      : FILE_WARNING_DEFAULT;

  const parsedFail = Number(process.env.BENCHMARK_FILE_FAIL_MS);
  const fileFailThreshold =
    !Number.isNaN(parsedFail) && parsedFail > 0 ? parsedFail : FILE_FAIL_DEFAULT;

  const exceeded: string[] = [];
  const warnings: string[] = [];

  files.forEach((file) => {
    if (file.duration > fileWarningThreshold) {
      warnings.push(`${file.name}: ${file.duration.toFixed(2)}ms`);
    }
    if (file.duration > fileFailThreshold) {
      exceeded.push(`${file.name}: ${file.duration.toFixed(2)}ms`);
    }
  });

  const suitePassed = suiteDuration < suiteThreshold;

  if (!suitePassed) {
    exceeded.push(
      `Suite duration: ${suiteDuration.toFixed(2)}ms (threshold: ${suiteThreshold}ms)`
    );
  }

  return {
    files,
    percentiles,
    suite: {
      duration: suiteDuration,
      failed: report.numFailedTests,
      passed: report.numPassedTests,
      tests: report.numTotalTests,
    },
    thresholds: {
      exceeded,
      fileFailThreshold,
      fileWarningThreshold,
      suitePassed,
      suiteThreshold,
      warnings,
    },
  };
}

/**
 * Format benchmark results for console output.
 */
function formatResults(results: BenchmarkResults): string {
  const lines: string[] = [];

  lines.push("=".repeat(60));
  lines.push("Test Performance Benchmark Results");
  lines.push("=".repeat(60));
  lines.push("");

  lines.push("Suite Summary:");
  lines.push(`  Total Tests: ${results.suite.tests}`);
  lines.push(`  Passed: ${results.suite.passed}`);
  lines.push(`  Failed: ${results.suite.failed}`);
  lines.push(`  Duration: ${results.suite.duration.toFixed(2)}ms`);
  lines.push("");

  lines.push("Percentiles:");
  lines.push(`  P50: ${results.percentiles.p50.toFixed(2)}ms`);
  lines.push(`  P90: ${results.percentiles.p90.toFixed(2)}ms`);
  lines.push(`  P95: ${results.percentiles.p95.toFixed(2)}ms`);
  lines.push("");

  if (results.thresholds.warnings.length > 0) {
    lines.push("⚠️  Slow Files (>500ms):");
    for (const w of results.thresholds.warnings) {
      lines.push(`  - ${w}`);
    }
    lines.push("");
  }

  if (results.thresholds.exceeded.length > 0) {
    lines.push("❌ Threshold Violations:");
    for (const e of results.thresholds.exceeded) {
      lines.push(`  - ${e}`);
    }
    lines.push("");
  }

  lines.push(
    results.thresholds.suitePassed
      ? `✅ Suite passed performance threshold (<${results.thresholds.suiteThreshold / 1000}s)`
      : `❌ Suite exceeded performance threshold (>=${results.thresholds.suiteThreshold / 1000}s)`
  );

  return lines.join("\n");
}

/**
 * Extract the value following a flag from CLI args.
 * Handles both `--flag value` and `--flag=value` formats.
 * Returns null if flag not found, no value provided, or value starts with "--".
 */
function getArgValue(args: string[], flag: string): string | null {
  // Check for --flag=value format
  for (const arg of args) {
    if (arg.startsWith(`${flag}=`)) {
      const value = arg.substring(flag.length + 1);
      return value.length > 0 ? value : null;
    }
  }

  // Check for --flag value format
  const index = args.indexOf(flag);
  if (index >= 0 && index + 1 < args.length && !args[index + 1].startsWith("-")) {
    return args[index + 1];
  }
  return null;
}

/**
 * Main benchmark execution.
 */
function main(): void {
  const args = process.argv.slice(2);

  // Validate and parse CLI arguments - ensure flag is not followed by another flag
  let inputPath = ".vitest-reports/vitest-report.json";
  const inputValue = getArgValue(args, "--input");
  if (inputValue !== null) {
    inputPath = inputValue;
  }

  let outputPath = "benchmark-summary.json";
  const outputValue = getArgValue(args, "--output");
  if (outputValue !== null) {
    outputPath = outputValue;
  }

  // Resolve paths relative to current working directory
  inputPath = resolve(inputPath);
  outputPath = resolve(outputPath);

  try {
    // Check input file exists BEFORE creating output directory
    if (!existsSync(inputPath)) {
      throw new Error(
        `Vitest JSON report not found at ${inputPath}. Run vitest with '--reporter=json --outputFile=${inputPath}' first.`
      );
    }

    mkdirSync(dirname(outputPath), { recursive: true });

    const results = parseVitestJson(inputPath);
    writeFileSync(outputPath, JSON.stringify(results, null, 2));
    console.log(formatResults(results));

    if (!results.thresholds.suitePassed || results.thresholds.exceeded.length > 0) {
      process.exit(1);
    }
  } catch (error) {
    console.error("Benchmark parsing failed:", error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
