/**
 * @fileoverview Next.js Proxy for CSP nonce + baseline security headers.
 */

import { type NextRequest, NextResponse } from "next/server";
import { COMMON_SECURITY_HEADERS, HSTS_HEADER } from "@/lib/security/headers";
import { createMiddlewareSupabase, getCurrentUser } from "@/lib/supabase/factory";
import { createServerLogger } from "@/lib/telemetry/logger";

type CspMode = "authed" | "public";

function base64EncodeBytes(value: Uint8Array): string {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(value).toString("base64");
  }
  // Edge runtime: Buffer is not available, but btoa is.
  let binary = "";
  for (const byte of value) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

function createNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return base64EncodeBytes(bytes);
}

function getCspModeFromPathname(pathname: string): CspMode {
  if (pathname === "/chat" || pathname.startsWith("/chat/")) return "authed";
  if (pathname === "/dashboard" || pathname.startsWith("/dashboard/")) return "authed";
  return "public";
}

const NEXT_BOOTSTRAP_HASHES = [
  // Next.js emits inline scripts that do not carry per-request nonces for static and
  // partially prerendered HTML. For public routes we keep `script-src` locked down
  // by allowing only known hashes (no `unsafe-inline`).
  //
  // Re-generate on Next.js upgrades or when public HTML changes:
  // - `pnpm build`
  // - `node scripts/csp/extract-inline-script-hashes.mjs`
  "'sha256-/QBfw030Vy5L/CZRzDHAg08GRDbIs7WRjlI17ePmTd0='",
  "'sha256-0LDbNUDsF1kfcl9a0wfp5EqiiBeALPMQap93898pLO8='",
  "'sha256-2+KQLga0tXyBbdHcjGt1+/tFZR12SXyjxpUnh9yh0es='",
  "'sha256-3W0kGFyHhxKnbDxzdYueKPYy3Jp+glPCjEjy9xpxGvU='",
  "'sha256-55oGYXgV2JWX8W9D8sm98+N0RRZlvNDyWxbcOrmMPdE='",
  "'sha256-5NU6mTJ5Z5HJuE7Os+6k4AeMhJeEK9nR5xnwRuNcL/I='",
  "'sha256-7mu4H06fwDCjmnxxr/xNHyuQC6pLTHr4M2E4jXw5WZs='",
  "'sha256-A19sqGca/Qp5Cc0tXxQ9pcXtCPPJMCNJ61NCHKUN4Og='",
  "'sha256-B/lAN+Y0+O4Roks0SFM4dj2RwNPSkf/wDWwfL3uLlrs='",
  "'sha256-CeEKCq6YUGmLVf+OIyKZwUPrjwMTLj7kg3zQ1dYRYig='",
  "'sha256-CgPZs6rK5cyOBbJv79qlGNiZ1433ORjmiADhgORukaQ='",
  "'sha256-Ei8YVH1TowC5NN5mqrHTYeehpKeQQGk4XQCio0G5Pls='",
  "'sha256-FwJBk7qSSwTV06xXQaUjHA/xK5ScXuhzD6wWFfCUoEo='",
  "'sha256-GiSGNb5T4MPUb8LrSxyRjp3Qms39KL0JsvuYIg4apFA='",
  "'sha256-H1A7/M7THJor+dmD+Fu5MjT5FX8pEEVA9uSBAqe+4FI='",
  "'sha256-HovBuvciOLh+x29S54UwVaNPh3rJiL+wKpApiQfOUsQ='",
  "'sha256-IMV49MnafgHT6Ss1hX2eSudFj9JfqOq9DPvL7eoa/Sc='",
  "'sha256-J3L0p4emIMMpvnQ0gAB4cKugMH/2hShHiasCsSVMS80='",
  "'sha256-JJUtUAWeWl6OSux+hRGoaMiIkJ4aC2ObLXJxUsREDlk='",
  "'sha256-Ja3UDobWYAL/TKTTvF2wOG+OBRis/ItJnEa9CVKnBhM='",
  "'sha256-KYYWmNwaIUMexfl/8IBKfZ4whLhNzzhxprcXhPLCkIU='",
  "'sha256-MM16lbtanDDhGQKE6t1ocMqTCrqEZKheViIhL+x3rWw='",
  "'sha256-Nf9IndKyZKsIXmDmv7ab1+RHrW31/licH5jJyKDYbO4='",
  "'sha256-OBTN3RiyCV4Bq7dFqZ5a2pAXjnCcCYeTJMO2I/LYKeo='",
  "'sha256-PDyc0s2AMQa7eHA5jP6urAuIux6oe1fOeaUlHlBi48s='",
  "'sha256-PcHDnumtURc75CRx3i5OsnnAq4fgurqBBxxtnJ6UzX8='",
  "'sha256-Pf1m47OgV7PfN+Ojm+hGLJiPqfVpqTlKRLua1ziyzfU='",
  "'sha256-QAlSewaQLi/NPCznjAZSyvQ72heD0VdxmNDDkZeCxgc='",
  "'sha256-RIf83i/u7VcXsOML119pEU/XiKU4+2FwMWExdgjXnLA='",
  "'sha256-RnmP1ZEpJDRx495i4lzlWhHdfjXDcO9fYK8w2es0bXQ='",
  "'sha256-S/RdQg0d4Qtyz5334ExnMd7VmQoyahNqdSj6yBkSNbE='",
  "'sha256-UTmW13f1CCDJIZyGQAtxb1ChLZmaO128wepuuGuzkBM='",
  "'sha256-WCol1dj1QW55h4gYCLZw6Rzbq/GwM214PM69tluRBks='",
  "'sha256-Y3YhfYl9DIAlGCxGS4tAlzwHS+p1jZ88NNs6xx3fWw4='",
  "'sha256-YisZmfcFYnIpuwCS3ML+0juLYWmCOvj3nx1sqsK/tso='",
  "'sha256-a1bwtR9HfzR7tUzKPeR4FJU0eTqTR8c2YdLGukEnCC8='",
  "'sha256-aVLRf3Evrzri0q2sQZI6aCUcQELJ1ZCZcCIkPN6hiU4='",
  "'sha256-b/ft9vHyXCXDUbwqDh4y55glbiJjz1dNjRzCtLZixl4='",
  "'sha256-bNja2grir1a/nA8NyopuDGAwkaAM0W+Jof5nJXJ6q5k='",
  "'sha256-cRNCVMt7FNGiNjlhanYjhHzjclrEwC+QKGkZ3CSTYog='",
  "'sha256-cnkT28w0YzF1Xac7qgu/vcIHmjeVXqu5YHLvelRjcDk='",
  "'sha256-e45CTV3T/5Xuvu7jPGxs+I4A1a48VuDzbb7d/gZJ/PQ='",
  "'sha256-eH3RP92lqVMbRJh9tTxPi+VVl12LdobAygY1exY4EPM='",
  "'sha256-eRsd3TMw0ftIb/y5t3GSMJKV/UExoPge7mmJGYlwDzk='",
  "'sha256-fTVrajXCc9HqzZ08CeKpR2nkmO+cidd7XLwMQSOER9Y='",
  "'sha256-gbJYSrtNLl1o3/MXXkxg3BgG9X3lNy+9bGuzCHLnQg0='",
  "'sha256-gnDPPi+Rc+5TS68YgHAgsTjCBmJh1KUwoXxGZKyi+BQ='",
  "'sha256-gt1iqEYN5IU0Su8mbnAsAi+cqmQwMyIfr5t0rkhXMd4='",
  "'sha256-iS7ieXQNtRaVJdqfvl7e2Xr6TsQHZq8ePzlhnkxp0U0='",
  "'sha256-jMecVqvoyEu7hnA5CbUlAjJXbHRwka7x4uChhr6KYvc='",
  "'sha256-k/L5o5LUtg5PcLLfNwxhHIegpcurppTpEwHdNhyuq+0='",
  "'sha256-kLKOOCxgQO+7VQVxvIKnkKYf6/SqrpTGXpc9ye7iKXw='",
  "'sha256-n46vPwSWuMC0W703pBofImv82Z26xo4LXymv0E9caPk='",
  "'sha256-p2+bNsre9MKrQF8zX/n0waqTIFrTt1m3ZPvDk6W3qQ0='",
  "'sha256-p7GE78bbMHDrE4IWzpiMSttAsTpUu7wwi5/wvnH54Os='",
  "'sha256-p7uJL4+uziBvz0v639f7vm1521E9jepWg32fnJR6y7U='",
  "'sha256-qtGJMfgguXYrZF28ua9+0mKHZXNcsIxH8vTaANzwjKQ='",
  "'sha256-r1mwz28YMrN0ZAlAYwm9iOkMj1I/aiXNS8W6dUyaYpI='",
  "'sha256-sukU4B2aIPgamzfyMSQOF1GZo/mhMDjJC7nfv3o2v24='",
  "'sha256-uBDdgE3SuqGUJacJ/1OnPjkpAg8ipm/qmgWYY+u6EGQ='",
  "'sha256-ugpajzx2pYqbVyokrlT9796YyEZINM1/Dza1CY5CGdo='",
  "'sha256-wpfaMctYaY7WdMZxeuNW4eiSbiglikZwQNYIYXLJW+M='",
  "'sha256-xhPLf2t8F7YPI2q4dvTbE8SIeCk4Ev8kP0sRQbk6Cyo='",
  "'sha256-xiTVNGxYs/HB+SVus1b18hWrDvFlL3+HxtsrkITOwDQ='",
  "'sha256-xl4N7r6AssI9u0zXFauqpxMtijR1U9xahY5eOw28ElQ='",
  "'sha256-xm4wFqfV7V4ojO8364T37U8qeC7/2o4N7BDKrowtYXk='",
] as const;

function buildCsp(options: { isDev: boolean; mode: CspMode; nonce?: string }): string {
  const { isDev, mode, nonce } = options;

  if (isDev) {
    // Development-only: relax CSP to avoid breaking HMR / tooling.
    // NOTE: If a nonce is present, browsers will ignore 'unsafe-inline', so we omit the nonce in dev.
    const scriptSrc = ["'self'", "'unsafe-eval'", "'unsafe-inline'"];

    const styleSrc = "'unsafe-inline'";
    const connectSrc = "'self' https: wss: http: ws:";

    const cspHeader = `
      default-src 'self';
      script-src ${scriptSrc.join(" ")};
      style-src 'self' ${styleSrc};
      img-src 'self' blob: data:;
      font-src 'self' data:;
      connect-src ${connectSrc};
      object-src 'none';
      base-uri 'self';
      form-action 'self';
      frame-ancestors 'none';
    `;

    return cspHeader.replace(/\s{2,}/g, " ").trim();
  } else {
    const reportUri =
      typeof process !== "undefined" ? process.env.CSP_REPORT_URI : undefined;
    const reportDirective = reportUri ? `report-uri ${reportUri};` : "";

    const connectSrc = "'self' https: wss:";
    const upgradeInsecureRequests = "upgrade-insecure-requests";

    if (mode === "public") {
      // Public routes are intended to remain statically renderable, so avoid per-request
      // nonces. Allow required inline scripts via hashes only.
      const scriptSrc = ["'self'", ...NEXT_BOOTSTRAP_HASHES];

      // Public pages frequently rely on inline styles emitted by the framework and UI libs.
      // Keep scripts locked down via hashes, but allow inline styles for compatibility.
      const styleSrc = "'unsafe-inline'";

      const cspHeader = `
        default-src 'self';
        script-src ${scriptSrc.join(" ")};
        style-src 'self' ${styleSrc};
        style-src-attr 'unsafe-inline';
        img-src 'self' blob: data:;
        font-src 'self' data:;
        connect-src ${connectSrc};
        object-src 'none';
        base-uri 'self';
        form-action 'self';
        frame-ancestors 'none';
        ${upgradeInsecureRequests};
        ${reportDirective}
      `;

      return cspHeader.replace(/\s{2,}/g, " ").trim();
    }

    if (!nonce) {
      throw new Error("CSP nonce is required for authenticated routes");
    }

    const scriptSrc = ["'self'", `'nonce-${nonce}'`, ...NEXT_BOOTSTRAP_HASHES];
    const styleSrc = `'nonce-${nonce}'`;
    // Allow dynamic inline style attributes (Radix popper positioning, etc.),
    // while still requiring nonces for <style> tags.
    const styleSrcAttr = "'unsafe-inline'";

    const cspHeader = `
      default-src 'self';
      script-src ${scriptSrc.join(" ")};
      style-src 'self' ${styleSrc};
      style-src-attr ${styleSrcAttr};
      img-src 'self' blob: data:;
      font-src 'self' data:;
      connect-src ${connectSrc};
      object-src 'none';
      base-uri 'self';
      form-action 'self';
      frame-ancestors 'none';
      ${upgradeInsecureRequests};
      ${reportDirective}
    `;

    return cspHeader.replace(/\s{2,}/g, " ").trim();
  }
}

// Shared with next.config.ts to keep static and dynamic headers in sync.
function applySecurityHeaders(headers: Headers, options: { isProd: boolean }): void {
  for (const header of COMMON_SECURITY_HEADERS) {
    headers.set(header.key, header.value);
  }

  if (options.isProd) {
    headers.set(HSTS_HEADER.key, HSTS_HEADER.value);
  }
}

export async function proxy(request: NextRequest) {
  const nodeEnv = typeof process !== "undefined" ? process.env.NODE_ENV : undefined;
  const isDev = nodeEnv === "development";
  const isProd = nodeEnv === "production";

  const pathname =
    request.nextUrl?.pathname ??
    (typeof request.url === "string" ? new URL(request.url).pathname : "/");

  const mode = getCspModeFromPathname(pathname);

  const nonce = mode === "authed" ? createNonce() : undefined;
  const contentSecurityPolicyHeaderValue = buildCsp({ isDev, mode, nonce });

  let response: NextResponse;
  let requestHeaders: Headers | null = null;

  if (mode === "authed") {
    requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-nonce", nonce ?? "");
    requestHeaders.set("Content-Security-Policy", contentSecurityPolicyHeaderValue);

    response = NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  } else {
    response = NextResponse.next();
  }

  // Supabase SSR cookie refresh (session maintenance) for Server Components.
  // This keeps auth cookies up-to-date without requiring a separate backend service.
  if (mode === "authed" && requestHeaders) {
    try {
      const supabase = createMiddlewareSupabase({
        cookies: {
          getAll: () => request.cookies.getAll(),
          setAll: (cookiesToSet) => {
            cookiesToSet.forEach(({ name, value }) => {
              if (value === "") {
                request.cookies.delete(name);
                return;
              }
              request.cookies.set(name, value);
            });

            const cookieHeader = request.cookies.toString();
            if (cookieHeader) {
              requestHeaders.set("cookie", cookieHeader);
            } else {
              requestHeaders.delete("cookie");
            }

            response = NextResponse.next({
              request: {
                headers: requestHeaders,
              },
            });

            cookiesToSet.forEach(({ name, options, value }) => {
              response.cookies.set(name, value, options);
            });
          },
        },
      });
      await getCurrentUser(supabase, {
        enableTracing: false,
        spanName: "proxy.supabase",
      });
    } catch (error) {
      // Ignore auth refresh failures in Proxy; downstream auth guards handle redirects/401s.
      const logger = createServerLogger("proxy.supabase");
      logger.warn("supabase_auth_refresh_failed", {
        error,
        path: pathname,
      });
    }
  }

  response.headers.set("Content-Security-Policy", contentSecurityPolicyHeaderValue);
  applySecurityHeaders(response.headers, { isProd });

  return response;
}

export const config = {
  matcher: [
    {
      missing: [
        { key: "next-router-prefetch", type: "header" },
        { key: "purpose", type: "header", value: "prefetch" },
      ],
      source:
        "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
    },
  ],
};
