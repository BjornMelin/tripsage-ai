#!/usr/bin/env node

/**
 * @fileoverview Playwright E2E web server wrapper (production build).
 *
 * Starts a lightweight mock Supabase Auth HTTP server (for SSR auth checks),
 * builds the Next.js app, and then launches the production server.
 *
 * This is intended for security-sensitive checks like CSP nonce enforcement.
 */

import { spawn } from "node:child_process";
import { cpSync, existsSync, mkdirSync } from "node:fs";
import http from "node:http";
import { join } from "node:path";

const DEFAULT_SUPABASE_URL = "http://127.0.0.1:54329";
const supabaseUrl = new URL(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? DEFAULT_SUPABASE_URL
);
const debugAuthRequests = process.env.E2E_DEBUG_AUTH === "1";

const supabasePort = Number.parseInt(supabaseUrl.port || "54329", 10);
console.error(`[e2e-webserver-prod] Mock Supabase Auth on ${supabaseUrl.origin}`);

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-origin": "*",
    "content-length": Buffer.byteLength(body).toString(),
    "content-type": "application/json; charset=utf-8",
  });
  res.end(body);
}

function sendNoContent(res, status) {
  res.writeHead(status, {
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-origin": "*",
  });
  res.end();
}

function buildMockUser() {
  const now = new Date().toISOString();
  return {
    // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
    app_metadata: {},
    aud: "authenticated",
    // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
    created_at: now,
    email: "test@example.com",
    // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
    email_confirmed_at: now,
    id: "00000000-0000-0000-0000-000000000000",
    role: "authenticated",
    // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
    updated_at: now,
    // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
    user_metadata: { full_name: "Test User" },
  };
}

function startMockSupabaseAuth() {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? "/", supabaseUrl);

    if (debugAuthRequests && url.pathname.startsWith("/auth/v1/")) {
      console.error(`[e2e-webserver-prod] ${req.method ?? "GET"} ${url.pathname}`);
    }

    if (req.method === "OPTIONS") {
      sendNoContent(res, 204);
      return;
    }

    if (url.pathname === "/health" && req.method === "GET") {
      sendJson(res, 200, { ok: true });
      return;
    }

    if (url.pathname === "/auth/v1/user" && req.method === "GET") {
      sendJson(res, 200, { user: buildMockUser() });
      return;
    }

    if (url.pathname === "/auth/v1/logout" && req.method === "POST") {
      sendNoContent(res, 204);
      return;
    }

    if (url.pathname.startsWith("/auth/v1/token") && req.method === "POST") {
      const user = buildMockUser();
      const nowSeconds = Math.floor(Date.now() / 1000);
      sendJson(res, 200, {
        // biome-ignore lint/style/useNamingConvention: Supabase token payload uses snake_case
        access_token: "e2e-access-token",
        // biome-ignore lint/style/useNamingConvention: Supabase token payload uses snake_case
        expires_at: nowSeconds + 3600,
        // biome-ignore lint/style/useNamingConvention: Supabase token payload uses snake_case
        expires_in: 3600,
        // biome-ignore lint/style/useNamingConvention: Supabase token payload uses snake_case
        refresh_token: "e2e-refresh-token",
        // biome-ignore lint/style/useNamingConvention: Supabase token payload uses snake_case
        token_type: "bearer",
        user,
      });
      return;
    }

    sendJson(res, 404, { error: "not_found" });
  });

  return new Promise((resolve, reject) => {
    server.on("error", (error) => {
      if (error.code === "EADDRINUSE") {
        reject(
          new Error(
            `Port ${supabasePort} is already in use. ` +
              "Free the port or set NEXT_PUBLIC_SUPABASE_URL to a URL with a different port (for example, http://127.0.0.1:54330)."
          )
        );
      } else {
        reject(error);
      }
    });
    server.listen(supabasePort, "127.0.0.1", () => {
      resolve(server);
    });
  });
}

function runNextBuild() {
  const shouldSkipBuild =
    process.env.E2E_SKIP_BUILD === "1" &&
    existsSync(join(".next", "standalone", "server.js"));
  if (shouldSkipBuild) {
    console.error("[e2e-webserver-prod] Skipping next build (E2E_SKIP_BUILD=1).");
    return Promise.resolve(undefined);
  }

  return new Promise((resolve, reject) => {
    const child = spawn("pnpm", ["exec", "next", "build"], { stdio: "inherit" });
    child.once("exit", (code) => {
      if (code === 0) resolve(undefined);
      else reject(new Error(`next build failed with exit code ${code ?? "unknown"}`));
    });
  });
}

function prepareStandaloneAssets() {
  const standaloneRoot = join(".next", "standalone");
  const standaloneNext = join(standaloneRoot, ".next");

  if (!existsSync(standaloneRoot)) {
    throw new Error(
      "Expected .next/standalone to exist after build (output: 'standalone')."
    );
  }

  mkdirSync(standaloneNext, { recursive: true });

  // Next.js standalone output does not include `public/` and `.next/static` by default.
  // Copy them so the standalone server can serve assets in local verification runs.
  cpSync("public", join(standaloneRoot, "public"), { force: true, recursive: true });
  cpSync(join(".next", "static"), join(standaloneNext, "static"), {
    force: true,
    recursive: true,
  });
}

function startNextProd() {
  const port = process.env.PORT ?? "3100";
  process.env.PORT = port;
  // This repo uses `output: "standalone"`, so `next start` is not supported.
  // Run the standalone server instead.
  const child = spawn("node", [".next/standalone/server.js"], {
    stdio: "inherit",
  });
  return child;
}

const mockServer = await startMockSupabaseAuth();
await runNextBuild();
prepareStandaloneAssets();
const nextChild = startNextProd();

let shuttingDown = false;

function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;

  try {
    mockServer.close();
  } catch {
    // ignore
  }
  if (nextChild.killed) {
    process.exit(0);
  }

  try {
    nextChild.kill("SIGTERM");
  } catch {
    process.exit(0);
  }

  const forceKill = setTimeout(() => {
    try {
      nextChild.kill("SIGKILL");
    } catch {
      // ignore
    }
    process.exit(0);
  }, 5_000);

  nextChild.once("exit", () => {
    clearTimeout(forceKill);
    process.exit(0);
  });
}

process.on("SIGINT", () => shutdown());
process.on("SIGTERM", () => shutdown());

nextChild.on("exit", (code) => {
  try {
    mockServer.close();
  } catch {
    // ignore
  }
  process.exit(code ?? 0);
});
