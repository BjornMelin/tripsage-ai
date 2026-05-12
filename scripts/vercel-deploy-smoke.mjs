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
const JSON_HEADERS = { "Content-Type": "application/json" };

function readArg(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index === -1) return fallback;
  const value = process.argv[index + 1];
  if (!value || value.startsWith("--")) return fallback;
  return value;
}

function normalizeBaseUrl(raw) {
  if (!raw) {
    throw new Error(
      "Missing deployment URL. Pass --url or set LIVE_SMOKE_URL, DEPLOYMENT_URL, or VERCEL_URL."
    );
  }
  const value = /^[a-z][a-z\d+\-.]*:/i.test(raw) ? raw : `https://${raw}`;
  const url = new URL(value);
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

function jsonPost(body) {
  return {
    body: JSON.stringify(body),
    headers: JSON_HEADERS,
    method: "POST",
    redirect: "manual",
  };
}

function assertStatus(response, label, expectedStatus) {
  if (response.status !== expectedStatus) {
    throw new Error(
      `Expected ${label} to return ${expectedStatus}, got ${response.status}`
    );
  }
  return { status: response.status };
}

function assertNoStore(path, cacheControl) {
  if (!cacheControl.toLowerCase().includes("no-store")) {
    throw new Error(`Expected ${path} Cache-Control no-store, got ${cacheControl}`);
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

function skipped(name, details = {}) {
  return { details, name, status: "skipped" };
}

async function checkHtmlShell(baseUrl, path, label) {
  const response = await request(baseUrl, path);
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.includes("text/html")) {
    throw new Error(
      `Expected ${label} HTML 2xx response, got ${response.status} ${contentType}`.trim()
    );
  }
  return { contentType, status: response.status };
}

async function checkJsonHealth(baseUrl, path, init) {
  const response = await request(baseUrl, path, init);
  const cacheControl = response.headers.get("cache-control") ?? "";
  const body = await response.json().catch(() => null);
  if (!response.ok || body?.status !== "ok") {
    throw new Error(`Expected ${path} ok, got ${response.status}`);
  }
  assertNoStore(path, cacheControl);
  return { cacheControl, status: response.status };
}

function checkAppShell(baseUrl) {
  return checkHtmlShell(baseUrl, "/", "app shell");
}

function checkHealth(baseUrl) {
  return checkJsonHealth(baseUrl, "/api/health");
}

async function checkUnauthenticatedAuth(baseUrl) {
  const response = await request(baseUrl, "/auth/me", { redirect: "manual" });
  return assertStatus(response, "/auth/me", 401);
}

function checkLoginShell(baseUrl) {
  return checkHtmlShell(baseUrl, "/login?next=%2Fdashboard", "login");
}

async function checkPostGuard(baseUrl, path, body, label) {
  const response = await request(baseUrl, path, jsonPost(body));
  return assertStatus(response, label, 401);
}

function checkByokHealth(baseUrl, byokHealthKey) {
  if (!byokHealthKey) {
    return skipped("byok_health_endpoint", {
      reason:
        "BYOK health key not provided; set LIVE_SMOKE_BYOK_HEALTHCHECK_KEY to enable.",
    });
  }

  return checkJsonHealth(baseUrl, "/api/health/byok", {
    headers: { "x-internal-key": byokHealthKey },
    redirect: "manual",
  });
}

function checkByokGuard(baseUrl) {
  return checkPostGuard(
    baseUrl,
    "/api/keys/validate",
    { apiKey: "sk-smoke-placeholder", service: "openai" },
    "protected BYOK route"
  );
}

function checkAttachmentUploadGuard(baseUrl) {
  return checkPostGuard(
    baseUrl,
    "/api/chat/attachments",
    {
      chatId: "chat-smoke-placeholder",
      files: [
        {
          contentType: "application/pdf",
          originalName: "itinerary.pdf",
          size: 1024,
        },
      ],
    },
    "protected attachment upload route"
  );
}

async function checkQstashRoutes(baseUrl) {
  const routeResponses = await requestAll(baseUrl, JOB_ROUTES, jsonPost({}));

  return {
    routes: routeResponses.map(({ path, response }) => {
      return {
        path,
        ...assertStatus(response, `${path} unsigned QStash request`, 401),
      };
    }),
  };
}

async function runCheck(name, fn) {
  try {
    const result = await fn();
    if (result?.status === "skipped") return result;
    return passed(name, result);
  } catch (error) {
    return failed(name, error);
  }
}

const baseUrl = normalizeBaseUrl(
  readArg(
    "--url",
    process.env.LIVE_SMOKE_URL ?? process.env.DEPLOYMENT_URL ?? process.env.VERCEL_URL
  )
);
const environment = readArg(
  "--environment",
  process.env.LIVE_SMOKE_ENVIRONMENT ?? "production"
);
const byokHealthKey = readArg(
  "--byok-health-key",
  process.env.LIVE_SMOKE_BYOK_HEALTHCHECK_KEY ?? process.env.BYOK_HEALTHCHECK_KEY
);
const checks = await Promise.all([
  runCheck("app_shell", () => checkAppShell(baseUrl)),
  runCheck("health_endpoint", () => checkHealth(baseUrl)),
  runCheck("auth_session_guard", () => checkUnauthenticatedAuth(baseUrl)),
  runCheck("authenticated_redirect_shell", () => checkLoginShell(baseUrl)),
  runCheck("byok_route_guard", () => checkByokGuard(baseUrl)),
  runCheck("byok_health_endpoint", () => checkByokHealth(baseUrl, byokHealthKey)),
  runCheck("attachment_upload_route_guard", () => checkAttachmentUploadGuard(baseUrl)),
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
