#!/usr/bin/env node

/**
 * @fileoverview Vercel deployment smoke checks for CI promotion.
 */

const JOB_ROUTES = [
  "/api/jobs/attachments-ingest",
  "/api/jobs/memory-sync",
  "/api/jobs/notify-collaborators",
  "/api/jobs/rag-index",
];

function readArg(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index === -1) return fallback;
  const value = process.argv[index + 1];
  if (!value || value.startsWith("--")) return fallback;
  return value;
}

function normalizeBaseUrl(raw) {
  if (!raw) {
    throw new Error("Missing --url");
  }
  const url = new URL(raw);
  url.pathname = "/";
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/$/, "");
}

async function request(baseUrl, path, init = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    return await fetch(new URL(path, baseUrl), {
      redirect: init.redirect ?? "follow",
      signal: controller.signal,
      ...init,
    });
  } finally {
    clearTimeout(timeout);
  }
}

function passed(name, details = {}) {
  return { details, name, status: "passed" };
}

function failed(name, error, details = {}) {
  return {
    details,
    error: error instanceof Error ? error.message : String(error),
    name,
    status: "failed",
  };
}

async function checkAppShell(baseUrl) {
  const response = await request(baseUrl, "/");
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.includes("text/html")) {
    throw new Error(
      `Expected HTML 2xx response, got ${response.status} ${contentType}`.trim()
    );
  }
  return { contentType, status: response.status };
}

async function checkHealth(baseUrl) {
  const response = await request(baseUrl, "/api/health");
  const cacheControl = response.headers.get("cache-control") ?? "";
  const body = await response.json().catch(() => null);
  if (!response.ok || body?.status !== "ok") {
    throw new Error(`Expected /api/health ok, got ${response.status}`);
  }
  if (!cacheControl.toLowerCase().includes("no-store")) {
    throw new Error(`Expected /api/health Cache-Control no-store, got ${cacheControl}`);
  }
  return { cacheControl, status: response.status };
}

async function checkUnauthenticatedAuth(baseUrl) {
  const response = await request(baseUrl, "/auth/me", { redirect: "manual" });
  if (response.status !== 401) {
    throw new Error(`Expected /auth/me to return 401, got ${response.status}`);
  }
  return { status: response.status };
}

async function checkLoginShell(baseUrl) {
  const response = await request(baseUrl, "/login?redirect_url=%2Fdashboard");
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.includes("text/html")) {
    throw new Error(
      `Expected login HTML 2xx response, got ${response.status} ${contentType}`.trim()
    );
  }
  return { contentType, status: response.status };
}

async function checkByokGuard(baseUrl) {
  const response = await request(baseUrl, "/api/keys/validate", {
    body: JSON.stringify({ apiKey: "sk-smoke-placeholder", service: "openai" }),
    headers: { "Content-Type": "application/json" },
    method: "POST",
    redirect: "manual",
  });
  if (response.status !== 401) {
    throw new Error(
      `Expected protected BYOK route to return auth guard 401, got ${response.status}`
    );
  }
  return { status: response.status };
}

async function checkQstashRoutes(baseUrl) {
  const results = [];
  for (const path of JOB_ROUTES) {
    const response = await request(baseUrl, path, {
      body: "{}",
      headers: { "Content-Type": "application/json" },
      method: "POST",
      redirect: "manual",
    });
    if (response.status !== 401) {
      throw new Error(
        `${path} expected unsigned QStash request to return 401, got ${response.status}`
      );
    }
    results.push({ path, status: response.status });
  }
  return { routes: results };
}

async function runCheck(name, fn, checks) {
  try {
    checks.push(passed(name, await fn()));
  } catch (error) {
    checks.push(failed(name, error));
  }
}

const baseUrl = normalizeBaseUrl(readArg("--url"));
const environment = readArg("--environment", "production");
const checks = [];

await runCheck("app_shell", () => checkAppShell(baseUrl), checks);
await runCheck("health_endpoint", () => checkHealth(baseUrl), checks);
await runCheck("auth_session_guard", () => checkUnauthenticatedAuth(baseUrl), checks);
await runCheck("authenticated_redirect_shell", () => checkLoginShell(baseUrl), checks);
await runCheck("byok_route_guard", () => checkByokGuard(baseUrl), checks);
await runCheck("qstash_job_route_guards", () => checkQstashRoutes(baseUrl), checks);

const failedChecks = checks.filter((check) => check.status === "failed");
const summary = {
  checks,
  environment,
  status: failedChecks.length === 0 ? "passed" : "failed",
  url: baseUrl,
};

console.log(JSON.stringify(summary, null, 2));

if (failedChecks.length > 0) {
  process.exit(1);
}
