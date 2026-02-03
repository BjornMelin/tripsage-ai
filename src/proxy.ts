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
  "sha256-0LDbNUDsF1kfcl9a0wfp5EqiiBeALPMQap93898pLO8=",
  "sha256-0PkU+1vARBslNzTnPNq/5xqHzJSVlHE0GGzjyOBWynI=",
  "sha256-1744nfkbVox6VZrFfe2jV7z9lhYOtT6NcjHAbb+65+Y=",
  "sha256-1OfGpn3bjfL2Xe/sVq6CI7aAbnvVoE9cdKE/u56UTmo=",
  "sha256-1y71/m6NdvzwigANwZUD9QA5nu1lyI+YwvA9bL23o+M=",
  "sha256-2d9AfoQyBzIZrZ5N0mxkHWwWLe3/l/KOM68x/rV2yS0=",
  "sha256-38WkgeFWZZQBOL76P+f3OE/IcV1nL0Nyf3WPPKIpGE4=",
  "sha256-3lyzGbunjcIo+Q/DMumc7WwN5UK95xJYvrLn4HJUUjQ=",
  "sha256-4O6l6Ro1jHwTnB/Bz9kdtxOUlR3mCSK21XniWr2UycQ=",
  "sha256-4ftQo3qr4V9imG0d7sezGnpLIG1SS5wavWSM21CUew4=",
  "sha256-5FANhbL/xJpjGPh7G4XRgiGXJ8jWfylAW5T5AFGQtyE=",
  "sha256-7mu4H06fwDCjmnxxr/xNHyuQC6pLTHr4M2E4jXw5WZs=",
  "sha256-9bTHnwaOa7/MePzJA7SbiheSziR0IJVjgZBnzHZzuVk=",
  "sha256-CgPZs6rK5cyOBbJv79qlGNiZ1433ORjmiADhgORukaQ=",
  "sha256-CzryjbKF95C9nWwOp17vJaDMMbhk1aT91lBajf8tnIY=",
  "sha256-DYymSCR0VfYoDwFFhTe8L7OhxECPJDHo58KWkqlq+eM=",
  "sha256-ET9ecDPpioQZAn00v/IUODFB65vxjfAt9PATC18ztMI=",
  "sha256-FIUpw6MZrObfeYwtTcPJRE10ilqNRuhdPfcUGaJbIWQ=",
  "sha256-FwJBk7qSSwTV06xXQaUjHA/xK5ScXuhzD6wWFfCUoEo=",
  "sha256-GiSGNb5T4MPUb8LrSxyRjp3Qms39KL0JsvuYIg4apFA=",
  "sha256-ImwG+fwHT6k6+Si4PXOSIpVcNaM2NTgYkadp3lHq1/M=",
  "sha256-IvdXx6AeqyRYM0cl2GTNNzNsyIdfhWOfwJZD9sKkQnU=",
  "sha256-LKLImlDiGgcr7dhJUA/h0r1Q07/PCrky9mPUUQid3Kc=",
  "sha256-LswaGg6fhdA0/kxZuPrcSrpbgRKqhBQsqhGBh0LwMpI=",
  "sha256-MLqHpVnnRA7fl/vLfMfoGVCaSJM4CrTr3uis3MNteUw=",
  "sha256-Nwq6HJSY2vONMgU4XfZNefG9/BmCLMZTgHoU8zHde9s=",
  "sha256-OBTN3RiyCV4Bq7dFqZ5a2pAXjnCcCYeTJMO2I/LYKeo=",
  "sha256-P0a2FzJOUTlqrJKUQpdflmOK0kfCrrg1Y2EH+mYFpPs=",
  "sha256-P4OouSDHCQSVN57dNsQKkdOlA968/o92u6+IVkbeXpQ=",
  "sha256-QAlSewaQLi/NPCznjAZSyvQ72heD0VdxmNDDkZeCxgc=",
  "sha256-R5+EVbYAXjRqm4w82h/88XKCNO7sTrH/jklPjJuaf/0=",
  "sha256-S84PVcrQhArWFZ8DsiNP9uV3R52KWlknVrnTIJGR6U0=",
  "sha256-URTdtxj9uArUkmRR1dyj9eHz4b262QXi1cj1lvSuP6o=",
  "sha256-X7kYCBgrtfN2fgDOA4BZWhxIiE4aGEVFEACX6bLV0pE=",
  "sha256-XB/MzvlEIdPxuY5XPZ9md5Pay0CM6c8JiLhmo3r/teM=",
  "sha256-Y8ahDrTPRGYKgzmBy0PclsYUbdD4uBxrS+muTkNdtDw=",
  "sha256-Y9tao9CYXHbualGOZIAcSUvaRi63IOk1elu1APdkR/I=",
  "sha256-YrwSh9UFxRJ2PbBHuvKN2rkbxHncx6bULjFMKPtkEPE=",
  "sha256-ZIEQxs4OBAJaGpuLY8L/uXXBPFTJzwCf+WFh3JuuinU=",
  "sha256-ai/xAr2UhBexlTGHnHddkEzz6t7vaMzRQS5uRR1mib8=",
  "sha256-apM3f3cK7u41DSZhu50y8H3XILQKaVoxrM9UNYJ6S7s=",
  "sha256-eS3Qo4NqKfi/kpli2KLhZ/jHSEqAR5folJqWJOr4r1o=",
  "sha256-fJbyfZ/CHdHBYj0j+bjHaYKLuOkBmbwgHijWT2+fQeg=",
  "sha256-gE6XPz8m59M4oNOnniv/OJMmgRbziElzJ+Np50sBSmQ=",
  "sha256-jG2tYm/hv9UmeJGkcu4YOXqED02HvHOR5YzinR6xZj4=",
  "sha256-kLKOOCxgQO+7VQVxvIKnkKYf6/SqrpTGXpc9ye7iKXw=",
  "sha256-kwFCRRUxdaXgmvHAJ3VgXZdAHtWt/WYoeiIcfBOryeo=",
  "sha256-lT1/Wj8nF6cvR+vdXDbv6oZHYl8P12yiMzk+GzDOXaM=",
  "sha256-mE2VD50hCMXxn32wTdNR68Tm6GesFvefVq4bDXMwlc4=",
  "sha256-maFXkpItPcq7HmTQC8Db13b9UoTC2YOayiIZOHdeFhM=",
  "sha256-mn3SfUaa33bo5vu78NoFnRY8xq6xprpbMkPXD2Ge2ZE=",
  "sha256-n46vPwSWuMC0W703pBofImv82Z26xo4LXymv0E9caPk=",
  "sha256-nWe8J5pQanEnDaFmarzzHDcBrnF33jg6M4xAy6gfLaA=",
  "sha256-nc1OZOGLeNUfOXPrsqaV0Ggt+1c14QaWvjClb9f5M50=",
  "sha256-p7GE78bbMHDrE4IWzpiMSttAsTpUu7wwi5/wvnH54Os=",
  "sha256-q/3MLLYQlF22es7NyM01xmJh6gXT0ePC9/V0MSuqghU=",
  "sha256-qtGJMfgguXYrZF28ua9+0mKHZXNcsIxH8vTaANzwjKQ=",
  "sha256-sjL5PjUzFSc2e9XSACe5fFtpCkAOfP5TZK/Idggh2ZE=",
  "sha256-so8vceBGWxg+sjZwJez3u/gOMJ+tW8o6/OU8AW9ZDEI=",
  "sha256-uL7u8INGN6LLu2zW0EBrxhlT5bUJ27IlI3UZf3N+Y5s=",
  "sha256-wpfaMctYaY7WdMZxeuNW4eiSbiglikZwQNYIYXLJW+M=",
  "sha256-x10s7aMgn4Kedk+Du1tUYVJVRqQqzS0KRb20wlL6Znw=",
  "sha256-xwYzKswfQmGorMideXJEf7er2Bwt7BMMWr3C10zc4vw=",
  "sha256-zaF93UfXXgkckCVe0kZkW9vlhJNDGlTAZw3eXZr7QrQ=",
  "sha256-zqlB3fkKex4v4hrHPOzC8Vh3PcAiK/QYmNiZh2hDK0E=",
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
