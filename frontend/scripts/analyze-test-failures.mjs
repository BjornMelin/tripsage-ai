/**
 * @fileoverview Analyze Vitest test failures and categorize them by type.
 * Usage: node scripts/analyze-test-failures.mjs [project-name]
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const project = process.argv[2] || "all";
const projects =
  project === "all"
    ? ["schemas", "integration", "api", "component", "unit"]
    : [project];

const failures = {
  asyncFlaky: [],
  behaviorDrift: [],
  browserEnv: [],
  other: [],
  routeContext: [],
  schema: [],
};

function categorizeFailure(_testFile, errorMessage) {
  const lower = errorMessage.toLowerCase();

  if (
    lower.includes("cookies") ||
    lower.includes("request scope") ||
    lower.includes("headers")
  ) {
    return "routeContext";
  }
  if (
    lower.includes("window is not defined") ||
    lower.includes("sessionstorage") ||
    lower.includes("localstorage") ||
    lower.includes("document is not defined")
  ) {
    return "browserEnv";
  }
  if (
    lower.includes("zod") ||
    lower.includes("safeParse") ||
    lower.includes("invalid_type_error")
  ) {
    return "schema";
  }
  if (
    lower.includes("timeout") ||
    lower.includes("exceeded") ||
    lower.includes("async") ||
    lower.includes("pending")
  ) {
    return "asyncFlaky";
  }
  if (
    lower.includes("expected") ||
    lower.includes("received") ||
    lower.includes("assertion")
  ) {
    return "behaviorDrift";
  }
  return "other";
}

function runProject(projectName) {
  return new Promise((resolve) => {
    const child = spawn(
      "pnpm",
      ["vitest", "run", `--project=${projectName}`, "--reporter=verbose"],
      {
        cwd: path.join(__dirname, ".."),
        stdio: ["ignore", "pipe", "pipe"],
      }
    );

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    child.on("exit", (code) => {
      const output = stdout + stderr;
      const lines = output.split("\n");

      let currentTest = null;
      let currentError = null;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        // Match test file and name
        if (line.match(/^\s*×\s+\|.*\|/)) {
          const match = line.match(/^\s*×\s+\|.*\|\s+(.+)$/);
          if (match) {
            currentTest = match[1].trim();
          }
        }

        // Match error messages
        if (
          line.includes("Error:") ||
          line.includes("TypeError:") ||
          line.includes("ReferenceError:")
        ) {
          currentError = line;
          if (currentTest) {
            const category = categorizeFailure(currentTest, currentError);
            failures[category].push({
              error: currentError.substring(0, 200),
              project: projectName,
              test: currentTest,
            });
          }
        }
      }

      resolve(code);
    });
  });
}

async function main() {
  console.log(`Analyzing failures for projects: ${projects.join(", ")}\n`);

  for (const proj of projects) {
    console.log(`Running ${proj}...`);
    await runProject(proj);
  }

  console.log("\n=== FAILURE SUMMARY ===\n");

  const categories = [
    { key: "routeContext", label: "Route Context Issues (cookies/headers)" },
    { key: "browserEnv", label: "Browser Environment Issues (window/storage)" },
    { key: "schema", label: "Schema/Fixture Issues (Zod validation)" },
    { key: "asyncFlaky", label: "Async/Flaky Issues (timeouts/hanging)" },
    { key: "behaviorDrift", label: "Behavior Drift (assertion mismatches)" },
    { key: "other", label: "Other Issues" },
  ];

  for (const { key, label } of categories) {
    const count = failures[key].length;
    console.log(`${label}: ${count}`);
    if (count > 0 && count <= 10) {
      failures[key].forEach((f) => {
        console.log(`  - [${f.project}] ${f.test}`);
        console.log(`    ${f.error}`);
      });
    } else if (count > 10) {
      failures[key].slice(0, 5).forEach((f) => {
        console.log(`  - [${f.project}] ${f.test}`);
      });
      console.log(`  ... and ${count - 5} more`);
    }
    console.log();
  }

  const total = Object.values(failures).reduce((sum, arr) => sum + arr.length, 0);
  console.log(`Total failures analyzed: ${total}`);
}

main().catch(console.error);

