#!/usr/bin/env tsx

/**
 * @fileoverview Test performance benchmark script for Vitest.
 * Collects test durations per file, calculates percentiles, and validates thresholds.
 */

import { execSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

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

  const report: VitestJsonReport = JSON.parse(
    readFileSync(jsonPath, "utf-8")
  );

  const files: TestFileMetrics[] = report.testResults.map((result) => {
    const duration = result.endTime - result.startTime;
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

  // Suite duration is the max of all file durations (since tests run in parallel)
  // For more accurate wall-clock time, use the overall startTime to endTime
  const suiteDuration = report.testResults.length > 0
    ? Math.max(...report.testResults.map((r) => r.endTime)) - report.startTime
    : files.reduce((sum, f) => sum + f.duration, 0);

  const percentiles = {
    p50: calculatePercentile(durations, 50),
    p90: calculatePercentile(durations, 90),
    p95: calculatePercentile(durations, 95),
  };

  const suiteThreshold = 10000; // 10s hard gate
  const fileWarningThreshold = 500; // 500ms soft warning
  const fileFailThreshold = 2000; // 2s hard fail (optional)

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
      suitePassed,
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
      ? "✅ Suite passed performance threshold (<10s)"
      : "❌ Suite exceeded performance threshold (>=10s)"
  );

  return lines.join("\n");
}

/**
 * Main benchmark execution.
 */
function main(): void {
  const outputDir = process.cwd();
  const jsonPath = join(outputDir, "test-results.json");

  console.log("Running Vitest benchmarks...");
  console.log("");

  try {
    // Run Vitest with JSON reporter
    execSync("pnpm test:run --reporter=json --outputFile=test-results.json", {
      cwd: outputDir,
      stdio: "inherit",
      encoding: "utf-8",
    });

    if (!existsSync(jsonPath)) {
      throw new Error("Vitest JSON report was not generated");
    }

    const results = parseVitestJson(jsonPath);

    // Write formatted results
    const summaryPath = join(outputDir, "benchmark-summary.json");
    writeFileSync(summaryPath, JSON.stringify(results, null, 2));

    console.log(formatResults(results));

    // Exit with error if thresholds exceeded
    if (!results.thresholds.suitePassed || results.thresholds.exceeded.length > 0) {
      process.exit(1);
    }
  } catch (error) {
    console.error("Benchmark execution failed:", error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

