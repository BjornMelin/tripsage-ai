/* eslint-disable no-console */
/**
 * @fileoverview Memory and timing monitor for Vitest test runs.
 * Wraps vitest run with periodic memory logging and total time tracking.
 * Usage: node scripts/test-memory-monitor.js [vitest args...]
 */

const { performance } = require("node:perf_hooks");
const { spawn } = require("node:child_process");
const path = require("node:path");

function logMemory(tag) {
  const m = process.memoryUsage();
  console.log(
    `[mem] ${tag} rss=${(m.rss / 1e6).toFixed(1)}MB heapUsed=${(m.heapUsed / 1e6).toFixed(1)}MB heapTotal=${(m.heapTotal / 1e6).toFixed(1)}MB external=${(m.external / 1e6).toFixed(1)}MB`
  );
}

const t0 = performance.now();
logMemory("start");

// Use pnpm/npm to resolve vitest correctly
const isPnpm = require("node:fs").existsSync(
  path.join(process.cwd(), "pnpm-lock.yaml")
);
const packageManager = isPnpm ? "pnpm" : "npm";
const child = spawn(packageManager, ["vitest", "run", ...process.argv.slice(2)], {
  env: process.env,
  shell: true,
  stdio: "inherit",
});

const interval = setInterval(() => logMemory("tick"), 5000);

child.on("exit", (code) => {
  clearInterval(interval);
  const t1 = performance.now();
  logMemory("end");
  console.log(`[time] ${((t1 - t0) / 1000).toFixed(2)}s total`);
  process.exit(code ?? 1);
});

child.on("error", (err) => {
  clearInterval(interval);
  console.error("[error] Failed to spawn vitest:", err);
  process.exit(1);
});
