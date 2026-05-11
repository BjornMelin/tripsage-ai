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
const RETRY_DELAY_MS = 1_000;
const REQUEST_ATTEMPTS = 3;

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

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request(baseUrl, path, init = {}) {
  let lastError;

  for (let attempt = 1; attempt <= REQUEST_ATTEMPTS; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15_000);
    try {
      const response = await fetch(new URL(path, baseUrl), {
        redirect: init.redirect ?? "follow",
        signal: controller.signal,
        ...init,
      });
      if (response.status < 500 || attempt === REQUEST_ATTEMPTS) {
        return response;
      }
    } catch (error) {
      lastError = error;
      if (attempt === REQUEST_ATTEMPTS) {
        throw error;
      }
    } finally {
      clearTimeout(timeout);
    }

    await delay(RETRY_DELAY_MS * attempt);
  }

  throw lastError ?? new Error(`Request failed for ${path}`);
}

function requestAll(baseUrl, paths, init) {
  return Promise.all(
    paths.map(async (path) => {
      const response = await request(baseUrl, path, init);
      return { path, response };
    })
  );
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
  const response = await request(baseUrl, "/login?next=%2Fdashboard");
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
  const routeResponses = await requestAll(baseUrl, JOB_ROUTES, {
    body: "{}",
    headers: { "Content-Type": "application/json" },
    method: "POST",
    redirect: "manual",
  });

  return {
    routes: routeResponses.map(({ path, response }) => {
      if (response.status !== 401) {
        throw new Error(
          `${path} expected unsigned QStash request to return 401, got ${response.status}`
        );
      }
      return { path, status: response.status };
    }),
  };
}

async function runCheck(name, fn) {
  try {
    return passed(name, await fn());
  } catch (error) {
    return failed(name, error);
  }
}

const baseUrl = normalizeBaseUrl(readArg("--url"));
const environment = readArg("--environment", "production");
const checks = await Promise.all([
  runCheck("app_shell", () => checkAppShell(baseUrl)),
  runCheck("health_endpoint", () => checkHealth(baseUrl)),
  runCheck("auth_session_guard", () => checkUnauthenticatedAuth(baseUrl)),
  runCheck("authenticated_redirect_shell", () => checkLoginShell(baseUrl)),
  runCheck("byok_route_guard", () => checkByokGuard(baseUrl)),
  runCheck("qstash_job_route_guards", () => checkQstashRoutes(baseUrl)),
]);

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
