/**
 * @fileoverview Next.js Proxy for CSP nonce + baseline security headers.
 */

import { type NextRequest, NextResponse } from "next/server";
import { COMMON_SECURITY_HEADERS, HSTS_HEADER } from "@/lib/security/headers";
import { createMiddlewareSupabase, getCurrentUser } from "@/lib/supabase/factory";
import { createServerLogger } from "@/lib/telemetry/logger";

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

function buildCsp(options: { nonce: string; isDev: boolean }): string {
  const { nonce, isDev } = options;

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
    // Next.js currently emits a small amount of inline bootstrap JS without a nonce.
    // Allow only that exact inline snippet via hash (no 'unsafe-inline').
    const allowlistedInlineScriptHashes = [
      // Next.js 16.1.1 emits this inline bootstrap snippet without a nonce.
      // Re-audit this hash when upgrading Next.js.
      // To regenerate: run `pnpm build`, find the inline script in .next/server/app/page.html,
      // and compute: echo -n '<script content>' | openssl dgst -sha256 -binary | base64
      // requestAnimationFrame(function(){$RT=performance.now()});
      "'sha256-7mu4H06fwDCjmnxxr/xNHyuQC6pLTHr4M2E4jXw5WZs='",
    ];

    const scriptSrc = ["'self'", `'nonce-${nonce}'`, ...allowlistedInlineScriptHashes];
    const styleSrc = `'nonce-${nonce}'`;
    // Allow dynamic inline style attributes (Radix popper positioning, etc.),
    // while still requiring nonces for <style> tags.
    const styleSrcAttr = "'unsafe-inline'";
    const connectSrc = "'self' https: wss:";
    const upgradeInsecureRequests = "upgrade-insecure-requests";

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

  const nonce = createNonce();
  const contentSecurityPolicyHeaderValue = buildCsp({ isDev, nonce });

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", contentSecurityPolicyHeaderValue);

  let response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Supabase SSR cookie refresh (session maintenance) for Server Components.
  // This keeps auth cookies up-to-date without requiring a separate backend service.
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
      path: request.nextUrl.pathname,
    });
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
