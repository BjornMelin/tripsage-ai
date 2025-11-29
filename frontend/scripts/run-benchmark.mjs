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

// Spawn timeout (30s for vitest, 10s for analysis)
const SPAWN_TIMEOUT_VITEST = 30_000;
const SPAWN_TIMEOUT_ANALYSIS = 10_000;

/**
 * Parse CLI arguments and return input/output paths
 */
function parseArgs() {
  const args = process.argv.slice(2);
  let inputDir = DEFAULT_REPORT_DIR;
  let inputFile = DEFAULT_REPORT_FILE;
  let outputFile = DEFAULT_SUMMARY_FILE;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--input" && args[i + 1]) {
      inputDir = path.dirname(args[i + 1]);
      inputFile = path.basename(args[i + 1]);
      i++;
    } else if (args[i]?.startsWith("--input=")) {
      const value = args[i].substring("--input=".length);
      inputDir = path.dirname(value);
      inputFile = path.basename(value);
    } else if (args[i] === "--output" && args[i + 1]) {
      outputFile = args[i + 1];
      i++;
    } else if (args[i]?.startsWith("--output=")) {
      outputFile = args[i].substring("--output=".length);
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
        reject(new Error(`Process exited with code ${code}`));
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
