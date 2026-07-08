/**
 * @fileoverview Next.js Proxy for CSP nonce + baseline security headers.
 */

import { type NextRequest, NextResponse } from "next/server";
import { COMMON_SECURITY_HEADERS, HSTS_HEADER } from "@/lib/security/headers";
import { createMiddlewareSupabase } from "@/lib/supabase/factory";
import { createServerLogger } from "@/lib/telemetry/logger";

type CspMode = "authed" | "public";

const AUTHED_ROUTE_PREFIXES = ["/chat", "/dashboard"] as const;
const DEFAULT_CSP_REPORT_URI = "/api/security/csp-report";

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
  const isAuthedRoute = AUTHED_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
  if (isAuthedRoute) return "authed";
  return "public";
}

function getCspReportUri(): string {
  const configuredReportUri =
    typeof process === "undefined" ? undefined : process.env.CSP_REPORT_URI;
  return configuredReportUri?.trim() || DEFAULT_CSP_REPORT_URI;
}

// Next.js emits inline bootstrap and flight scripts. Authenticated routes stay
// locked down with a per-request nonce plus known static hashes.
//
// Re-generate on Next.js upgrades or when public HTML changes:
// - `pnpm build`
// - `node scripts/csp/extract-inline-script-hashes.mjs`
const NEXT_BOOTSTRAP_HASHES = [
  "sha256-+DemX5JlsbV0IMlg/3jzjLlpujVlrRDmF2IdaWY5izo=",
  "sha256-+O717fN7wZGQE1R6cvAEanBowUFscCGtbFcCoss2xgE=",
  "sha256-3WK0gOFombc1uxqjP4N3etfgOdq9OTeUCq8E0Kgitxk=",
  "sha256-4IHY74vYM6RkDaLPF7D/LVzn/iidJxoaZS3zyiHT5gc=",
  "sha256-4X34L88Kkojo2pgT7IPLqjcMGOhF1mTVYtRI0UXm7K4=",
  "sha256-7kC+RQPDtofk5xHPBtxvH15YeNZR+u7r3OkcYvZbwHA=",
  "sha256-7mu4H06fwDCjmnxxr/xNHyuQC6pLTHr4M2E4jXw5WZs=",
  "sha256-BNV3rSHeAfMgCjqXMs46BSKkv2pcy9WvXTZKHnlNhpU=",
  "sha256-bsG2hf4IGVfHInNQp+NXhaYb98rylARxIOSgJNNlHVk=",
  "sha256-c/qCfeHPE0y6ZrCLQNF23GBxf1hLziP6n7O9CMP5q14=",
  "sha256-CgPZs6rK5cyOBbJv79qlGNiZ1433ORjmiADhgORukaQ=",
  "sha256-CK/7EV++/pd6c8ag6gB93MRHrdfoouxt+zzPK262m3o=",
  "sha256-DSjFC0JrPQ4YF/EuvX3sD+rpIJQw6XvUewQv+xPMpis=",
  "sha256-eIox9Mf+TbuQhEKOyFxx3b92O5x2Vyhle0//Lhbb6WI=",
  "sha256-EPW1JCh0x/D/68An0VnZB/sb9L2DDxjikLv69GoEklk=",
  "sha256-fBVjGJRZP4/Dj+SZH11zMp4z8kJGLXrMRtoQEf6SkVY=",
  "sha256-gi0rwFWnYB6iJ/vuKWObtTNlqcoMHKVJKgIkwjKJ2GE=",
  "sha256-hsv4OT8zpnUigF2ZY0r4R9zLe/BqB+tZV0+ep+CExr0=",
  "sha256-htHgK01uJUE3v+dbub8OxG1dbL/w4A9Wc4YhF65kkpM=",
  "sha256-hXi5LStyJHvvMSCO3SssU77eFK16uA/qhoWV8sF4yCA=",
  "sha256-I/Xp3lq/QrklLRC+sPgaQrzM5NKs0Z8+QKLIcYS8gQU=",
  "sha256-iAxn6O3IdwBkUQIMX4MQnwq3AehHWa6mIOt6pMqWCTM=",
  "sha256-ieiuVjjqMchxJ5yVTmZMfr52YF5XksPAN+q1fvxAtAo=",
  "sha256-if9n/ixLrX5/DDVtqP3+4L02OahJyILye4+2YErgCBU=",
  "sha256-IP/AMfg8tIKDPAU4luFZ/70B1+6gZ1GSKHP2EStYY4w=",
  "sha256-iYR2Pqngmn+cdPap2H5em9YZOGyRagYXOa5k1KLtAE4=",
  "sha256-JDHVZS2nztTyXLXSnlnrv3DcsnF6194JqBOsebEAb/Y=",
  "sha256-jDyPtQxOQrzR5xgZzKAht25ZLFgX3nLHQQ12JdT3iNk=",
  "sha256-JETYzpVVpvcf3YtIGU2sQmL0KGwki1Tz5yxnRJP5qdA=",
  "sha256-JfVSQWIhItthM3cM3NNe+Pq+DwJpcfa6ajWvyuEdIIo=",
  "sha256-l1YQxr0vro2R0CxfmX7+9Du64MhusHsIRWdcZeO0ONI=",
  "sha256-liV7w401bAYYqb6ZINFtlCnx61JPAlufkeGNyAVJAVw=",
  "sha256-m6IBo6hkBs6op1C29Sze/gfg/a9WtvJ/102BHohBPmI=",
  "sha256-Matv/PSX1//jRTKMJHvJLItNEvKcoyC3CumepzcnW94=",
  "sha256-MyNgV+cLwdHUhJ4JGQZWukBJw0Rg87OGSlhaLeGznWA=",
  "sha256-mZlKL4aDTUKa+Qh0mK4SoZjjKHz92K/f9EamJbjWI5g=",
  "sha256-n46vPwSWuMC0W703pBofImv82Z26xo4LXymv0E9caPk=",
  "sha256-nzwxCUAA3shb9IBBq/hkQt1aAuGMNOdUdUUgVMj6D1o=",
  "sha256-o+Gg+GgAhFcwbci++CaCknFXE8AJYYEuCSNAZEkV6Sc=",
  "sha256-OBTN3RiyCV4Bq7dFqZ5a2pAXjnCcCYeTJMO2I/LYKeo=",
  "sha256-oJ8i+d3Lz5TVO7Q67AySfkWHabwSuct9E490VaGtC+Q=",
  "sha256-oz5YyvRCORA/R1VIWZUUiVyMNzAGwakzlO5Ob8VlRMI=",
  "sha256-p7GE78bbMHDrE4IWzpiMSttAsTpUu7wwi5/wvnH54Os=",
  "sha256-pCaLnO4X/4dUZYuMw0RVHOmVB5Ssab17jOcErYl2w3Q=",
  "sha256-PI844N/49CU7hTIwsNmuDajKN4/hrUs1RXjZryDc1wI=",
  "sha256-pXT8wJHd3+C8yNDE/3Ftz6HiaspXCxtxWbQq/4W7Y4c=",
  "sha256-QAlSewaQLi/NPCznjAZSyvQ72heD0VdxmNDDkZeCxgc=",
  "sha256-qE6aeiWxBc+wJhrUgOpgqDtAjWD9sB7wQPu2PnrdFq4=",
  "sha256-qjAlqy2cqAq6Nec6rOxqXciDHCoRCzqnOpT+BvFjrpA=",
  "sha256-qjP1vfvA2v0F3GtIPg39u+fyp/aluP3EF4nOglREOA8=",
  "sha256-Qrn6fJuu5PKaviG36JddvFicgkjrgaZ6dK1ac1tfqww=",
  "sha256-R/akwlmSE+xpaWMH9qFaxyohM5VUDm2JeZ+jnTjSXCM=",
  "sha256-RkcVCE6veF20xS8u6j9M4r2hascZpFKdBtXuVECP7f4=",
  "sha256-RyefFNsbE2KHqLjuai/sIYG/0VZKreCFQrE1zTRbVyk=",
  "sha256-sAiMI/4o5h5PHvNfs6Qt3QQjTd1W4eAXCiGBBHOLke4=",
  "sha256-t1rpsjQFJvBcWm/zLRIR5Z9HrSjTFzwvy1vUf5uK32k=",
  "sha256-TEBs8dCUqIipOJ+sEbmjCrLE0sIv81B0mB5FugwYYLM=",
  "sha256-tLNtbzxq1mmARcU3XnTVMxsmnDCy+F3hasKew4bPe6s=",
  "sha256-tmuOSq88RAMLglFTr8alf236Et2tJsyU5b9/pmpNBao=",
  "sha256-tSznwTPNFqNwR5e840VWfhwGzXE3wD/YBR5mqnUiruM=",
  "sha256-vjsGr6iFR0nUBRIRbDTzXQlVy8vlNJgJUmgKqT7Tzu0=",
  "sha256-w83nFxRFqtMjKDWi6Sby8R6jtT+35+P49VO2Ez29WUs=",
  "sha256-wwGGJYEH0hY5/PBLiiE3Oq8w7+fXcVXB2WMbn2lHeoY=",
  "sha256-ylT70f1kDUmB2CjFKk+6mId4vkm7NkpMaiOB36IHSO0=",
  "sha256-zixtbB78RC6JpYxj6Ff102C3+aJnWUd3TIflWzaElmY=",
  "sha256-ZO/gOAe3OHg57hlNV7Hoxd2SQb26Gbo6rp6CHUXJV0s=",
  "sha256-ZZ7KHscOVL7lM4V1jUmkIiD/PCtC8RnorrdUY8PD1k0=",
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
    const reportDirective = `report-uri ${getCspReportUri()};`;

    const connectSrc = "'self' https: wss:";
    const upgradeInsecureRequests = "upgrade-insecure-requests";

    if (mode === "public") {
      // Public pages are statically renderable, so they cannot receive a per-request nonce.
      // Next.js 16.2 also emits live inline flight payloads that are not fully represented
      // by build-time hash extraction. Keep strict nonce enforcement on authenticated routes
      // and use the framework-compatible public policy here.
      const scriptSrc = ["'self'", "'unsafe-inline'"];

      // Public pages frequently rely on inline styles emitted by the framework and UI libs.
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

function buildPublicReportOnlyCsp(): string {
  const reportDirective = `report-uri ${getCspReportUri()};`;
  const scriptSrc = [
    "'self'",
    ...NEXT_BOOTSTRAP_HASHES.map((hash) => `'${hash}'`),
    "'report-sample'",
  ];

  const cspHeader = `
    default-src 'self';
    script-src ${scriptSrc.join(" ")};
    style-src 'self' 'unsafe-inline';
    style-src-attr 'unsafe-inline';
    img-src 'self' blob: data:;
    font-src 'self' data:;
    connect-src 'self' https: wss:;
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    upgrade-insecure-requests;
    ${reportDirective}
  `;

  return cspHeader.replace(/\s{2,}/g, " ").trim();
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

/**
 * Next.js middleware proxy that applies CSP headers and refreshes Supabase auth cookies.
 *
 * @param request - The incoming Next.js request to process.
 * @returns The response with security headers and CSP applied.
 */
export async function proxy(request: NextRequest) {
  const nodeEnv = typeof process === "undefined" ? undefined : process.env.NODE_ENV;
  const isDev = nodeEnv === "development";
  const isProd = nodeEnv === "production";

  const pathname =
    request.nextUrl?.pathname ??
    (typeof request.url === "string" ? new URL(request.url).pathname : "/");

  const mode = getCspModeFromPathname(pathname);

  const nonce = !isDev && mode === "authed" ? createNonce() : undefined;
  const contentSecurityPolicyHeaderValue = buildCsp({ isDev, mode, nonce });
  const reportOnlyContentSecurityPolicyHeaderValue =
    isProd && mode === "public" ? buildPublicReportOnlyCsp() : null;

  let response: NextResponse;
  let requestHeaders: Headers | null = null;

  if (mode === "authed") {
    requestHeaders = new Headers(request.headers);
    if (nonce) {
      requestHeaders.set("x-nonce", nonce);
    }
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
      await supabase.auth.getClaims();
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
  if (reportOnlyContentSecurityPolicyHeaderValue) {
    response.headers.set(
      "Content-Security-Policy-Report-Only",
      reportOnlyContentSecurityPolicyHeaderValue
    );
  }
  applySecurityHeaders(response.headers, { isProd });

  return response;
}

/**
 * Next.js middleware matcher configuration excluding static assets and prefetch requests.
 */
export const config = {
  matcher: [
    {
      missing: [
        { key: "next-router-prefetch", type: "header" },
        { key: "purpose", type: "header", value: "prefetch" },
      ],
      source:
        "/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|manifest.webmanifest|manifest.json|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
    },
  ],
};
