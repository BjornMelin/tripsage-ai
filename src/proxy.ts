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

// Next.js emits inline scripts that do not carry per-request nonces for static and
// partially prerendered HTML. For public routes we keep `script-src` locked down
// by allowing only known hashes (no `unsafe-inline`).
//
// Re-generate on Next.js upgrades or when public HTML changes:
// - `pnpm build`
// - `node scripts/csp/extract-inline-script-hashes.mjs`
const NEXT_BOOTSTRAP_HASHES = [
  "sha256-/QBfw030Vy5L/CZRzDHAg08GRDbIs7WRjlI17ePmTd0=",
  "sha256-0IGlvpiSHJVkhXLAEqgRhxT7ps8msHdJ28AY6g3YECU=",
  "sha256-0LDbNUDsF1kfcl9a0wfp5EqiiBeALPMQap93898pLO8=",
  "sha256-2+KQLga0tXyBbdHcjGt1+/tFZR12SXyjxpUnh9yh0es=",
  "sha256-3W0kGFyHhxKnbDxzdYueKPYy3Jp+glPCjEjy9xpxGvU=",
  "sha256-4tIVlDViqIdvuqn9/u7jq8QlhYOHS/l8K5O8GxgQ1xE=",
  "sha256-4ym1WXJltKwu2WGff63yyvQXa2DmgqwGYgsZuP+nssQ=",
  "sha256-55oGYXgV2JWX8W9D8sm98+N0RRZlvNDyWxbcOrmMPdE=",
  "sha256-5NU6mTJ5Z5HJuE7Os+6k4AeMhJeEK9nR5xnwRuNcL/I=",
  "sha256-6IKjbu50us5hwbiJEQL4verXAk3LTATwWT+fXXG84SI=",
  "sha256-6Pa2VR2AHgeQLi63zyiGtmrQd+CesTUpJ9BWJW72Qrw=",
  "sha256-6QtCiK5kX+Q07tWdpn3aO/+2rroJ0K0lRKj63Q+7wqk=",
  "sha256-7B8j5BAlqb+JRQYbEPn7e3PW7RU9nZ/DGxRCfAfkxck=",
  "sha256-7mu4H06fwDCjmnxxr/xNHyuQC6pLTHr4M2E4jXw5WZs=",
  "sha256-A19sqGca/Qp5Cc0tXxQ9pcXtCPPJMCNJ61NCHKUN4Og=",
  "sha256-a1bwtR9HfzR7tUzKPeR4FJU0eTqTR8c2YdLGukEnCC8=",
  "sha256-AfTt9rnq/DtgSVx+XIZU5VK3WxiE+Mlv7d5daOIcVSI=",
  "sha256-aVLRf3Evrzri0q2sQZI6aCUcQELJ1ZCZcCIkPN6hiU4=",
  "sha256-b/ft9vHyXCXDUbwqDh4y55glbiJjz1dNjRzCtLZixl4=",
  "sha256-CgPZs6rK5cyOBbJv79qlGNiZ1433ORjmiADhgORukaQ=",
  "sha256-cnkT28w0YzF1Xac7qgu/vcIHmjeVXqu5YHLvelRjcDk=",
  "sha256-e45CTV3T/5Xuvu7jPGxs+I4A1a48VuDzbb7d/gZJ/PQ=",
  "sha256-eH3RP92lqVMbRJh9tTxPi+VVl12LdobAygY1exY4EPM=",
  "sha256-Ei8YVH1TowC5NN5mqrHTYeehpKeQQGk4XQCio0G5Pls=",
  "sha256-eRsd3TMw0ftIb/y5t3GSMJKV/UExoPge7mmJGYlwDzk=",
  "sha256-fTVrajXCc9HqzZ08CeKpR2nkmO+cidd7XLwMQSOER9Y=",
  "sha256-FwJBk7qSSwTV06xXQaUjHA/xK5ScXuhzD6wWFfCUoEo=",
  "sha256-GiSGNb5T4MPUb8LrSxyRjp3Qms39KL0JsvuYIg4apFA=",
  "sha256-gnDPPi+Rc+5TS68YgHAgsTjCBmJh1KUwoXxGZKyi+BQ=",
  "sha256-h7gZ/Zjtdk+wvZGqAAfksQk3gqm/k+PJogND+yFisWU=",
  "sha256-HovBuvciOLh+x29S54UwVaNPh3rJiL+wKpApiQfOUsQ=",
  "sha256-idVhEf1dBjUWpYnDhsTPEYCiei7RR7M8v7CyNNqJn4A=",
  "sha256-IMV49MnafgHT6Ss1hX2eSudFj9JfqOq9DPvL7eoa/Sc=",
  "sha256-Ja3UDobWYAL/TKTTvF2wOG+OBRis/ItJnEa9CVKnBhM=",
  "sha256-k6ESPux+cSHACPfYtsMlo5NNUjeDDwR974vU87PwOm0=",
  "sha256-kLKOOCxgQO+7VQVxvIKnkKYf6/SqrpTGXpc9ye7iKXw=",
  "sha256-MM16lbtanDDhGQKE6t1ocMqTCrqEZKheViIhL+x3rWw=",
  "sha256-n46vPwSWuMC0W703pBofImv82Z26xo4LXymv0E9caPk=",
  "sha256-Nf9IndKyZKsIXmDmv7ab1+RHrW31/licH5jJyKDYbO4=",
  "sha256-OBTN3RiyCV4Bq7dFqZ5a2pAXjnCcCYeTJMO2I/LYKeo=",
  "sha256-oU7GAUKBwSZ7nsYIhAGjJd0C/kl/YAylU8BP5tS6UQ8=",
  "sha256-p7GE78bbMHDrE4IWzpiMSttAsTpUu7wwi5/wvnH54Os=",
  "sha256-PDyc0s2AMQa7eHA5jP6urAuIux6oe1fOeaUlHlBi48s=",
  "sha256-Pf1m47OgV7PfN+Ojm+hGLJiPqfVpqTlKRLua1ziyzfU=",
  "sha256-QAlSewaQLi/NPCznjAZSyvQ72heD0VdxmNDDkZeCxgc=",
  "sha256-qJDeOTZsgpLlY1kVXRs0zAZyDNxLXCIo8a9QDEyq/d4=",
  "sha256-Qlbjr0UN+at3i3pGS1aXomyXHaj9IQ4Ud3VouG170Kc=",
  "sha256-qtGJMfgguXYrZF28ua9+0mKHZXNcsIxH8vTaANzwjKQ=",
  "sha256-QvhkCC2jDw4P2FN/lUdAzBi12i4RvoBp77duZrlnKks=",
  "sha256-r1mwz28YMrN0ZAlAYwm9iOkMj1I/aiXNS8W6dUyaYpI=",
  "sha256-RIf83i/u7VcXsOML119pEU/XiKU4+2FwMWExdgjXnLA=",
  "sha256-S/RdQg0d4Qtyz5334ExnMd7VmQoyahNqdSj6yBkSNbE=",
  "sha256-S8hFtOq4qAqmEx+613Ve8OjFIglIUTLfHYetngQeZjA=",
  "sha256-SQzADRu62lo73RV/ciR4eexbEInbsoum1JqwZpbsnIs=",
  "sha256-Sr+AgdIhVyrBnsx5/r2FqAW6lpu7YDoY8N/eLSlkuyk=",
  "sha256-txNU1a77fc+UsjMrJWYQJZnk30dCuL2FOQy63ONZAIo=",
  "sha256-TzqsYqIh0tE1BisYtCmu6QYe0HcocFQ1+eIN9Nj6Z0c=",
  "sha256-uBDdgE3SuqGUJacJ/1OnPjkpAg8ipm/qmgWYY+u6EGQ=",
  "sha256-ugpajzx2pYqbVyokrlT9796YyEZINM1/Dza1CY5CGdo=",
  "sha256-UTmW13f1CCDJIZyGQAtxb1ChLZmaO128wepuuGuzkBM=",
  "sha256-WCol1dj1QW55h4gYCLZw6Rzbq/GwM214PM69tluRBks=",
  "sha256-wpfaMctYaY7WdMZxeuNW4eiSbiglikZwQNYIYXLJW+M=",
  "sha256-xiTVNGxYs/HB+SVus1b18hWrDvFlL3+HxtsrkITOwDQ=",
  "sha256-zQgj2ygYTjQmaJg40aSNZhdJ9+ye3bEZV+qT105nzd8=",
  "sha256-zSXCnMosd2qYCOmRAriBuZCEjnJJVzJHkaSoeO+z/SI=",
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
      const scriptSrc = ["'self'", ...NEXT_BOOTSTRAP_HASHES.map((hash) => `'${hash}'`)];

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

    const scriptSrc = [
      "'self'",
      `'nonce-${nonce}'`,
      ...NEXT_BOOTSTRAP_HASHES.map((hash) => `'${hash}'`),
    ];
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
