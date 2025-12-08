#!/usr/bin/env node

/**
 * @fileoverview Run Vitest benchmark tests and analyze results.
 * Ensures output directory exists, runs vitest with reporters, and analyzes the report.
 * Usage: node scripts/run-benchmark.mjs [--input path] [--output path]
 */

import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// biome-ignore lint/style/useNamingConvention: __dirname is Node.js standard
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, "..");

// Default paths
const DEFAULT_REPORT_DIR = ".vitest-reports";
const DEFAULT_REPORT_FILE = "vitest-report.json";
const DEFAULT_SUMMARY_FILE = "benchmark-summary.json";

// Spawn timeouts are configurable for CI robustness
const SPAWN_TIMEOUT_VITEST = (() => {
  const parsed = Number.parseInt(process.env.VITEST_BENCHMARK_TIMEOUT_MS ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 60_000;
})();

const SPAWN_TIMEOUT_ANALYSIS = (() => {
  const parsed = Number.parseInt(
    process.env.VITEST_BENCHMARK_ANALYSIS_TIMEOUT_MS ?? "",
    10
  );
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 10_000;
})();

/**
 * Parse CLI arguments and return input/output paths
 */
function parseArgs() {
  const args = process.argv.slice(2);
  let inputDir = DEFAULT_REPORT_DIR;
  let inputFile = DEFAULT_REPORT_FILE;
  let outputFile = DEFAULT_SUMMARY_FILE;

  for (let i = 0; i < args.length; i++) {
    const nextArg = args[i + 1];
    if (args[i] === "--input" && nextArg && !nextArg.startsWith("--")) {
      inputDir = path.dirname(nextArg);
      inputFile = path.basename(nextArg);
      i++;
    } else if (args[i]?.startsWith("--input=")) {
      const value = args[i].substring("--input=".length);
      if (value !== "") {
        inputDir = path.dirname(value);
        inputFile = path.basename(value);
      }
    } else if (args[i] === "--output" && nextArg && !nextArg.startsWith("--")) {
      outputFile = nextArg;
      i++;
    } else if (args[i]?.startsWith("--output=")) {
      const value = args[i].substring("--output=".length);
      if (value !== "") {
        outputFile = value;
      }
    } else if (args[i] === "--help") {
      console.log(
        "Usage: node scripts/run-benchmark.mjs [--input path] [--output path]"
      );
      process.exit(0);
    }
  }

  const reportDir = path.join(projectRoot, inputDir);
  const reportPath = path.join(reportDir, inputFile);
  const summaryPath = path.join(projectRoot, outputFile);

  // Ensure output directory exists
  mkdirSync(reportDir, { recursive: true });

  return { reportPath, summaryPath };
}

const { reportPath, summaryPath } = parseArgs();

/**
 * Spawn a child process with timeout and cleanup
 */
function spawnWithTimeout(command, args, timeoutMs) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: projectRoot,
      stdio: "inherit",
    });

    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
    }, timeoutMs);

    child.on("exit", (code, signal) => {
      clearTimeout(timeout);
      if (timedOut) {
        reject(new Error(`Process timed out after ${timeoutMs}ms (signal: ${signal})`));
      } else if (code === 0) {
        resolve(code);
      } else {
        // Distinguish between test failures and infra errors for vitest
        if (
          command === "pnpm" &&
          Array.isArray(args) &&
          args.length > 0 &&
          args[0] === "vitest" &&
          code === 1
        ) {
          reject(new Error("Vitest exited with code 1: Test failures detected."));
        } else {
          reject(
            new Error(
              `Process exited with code ${code}. This may indicate an infrastructure or environment error.`
            )
          );
        }
      }
    });

    child.on("error", (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}

/**
 * Run vitest and generate JSON report
 */
function runVitest() {
  return spawnWithTimeout(
    "pnpm",
    [
      "vitest",
      "run",
      "--reporter=dot",
      "--reporter=json",
      `--outputFile=${reportPath}`,
    ],
    SPAWN_TIMEOUT_VITEST
  );
}

/**
 * Run benchmark analysis tool
 */
function analyzeBenchmarks() {
  return spawnWithTimeout(
    "pnpm",
    [
      "tsx",
      "scripts/benchmark-tests.ts",
      `--input=${reportPath}`,
      `--output=${summaryPath}`,
    ],
    SPAWN_TIMEOUT_ANALYSIS
  );
}

async function main() {
  try {
    console.log("Running vitest benchmarks...");
    await runVitest();

    console.log("Analyzing benchmark results...");
    await analyzeBenchmarks();

    console.log("✓ Benchmark complete");
    process.exit(0);
  } catch (error) {
    console.error("✗ Benchmark failed:", error);
    process.exit(1);
  }
}

main();
