/**
 * @fileoverview Client IP extraction with proxy header trust validation.
 */

// SECURITY: Proxy headers (X-Forwarded-For, X-Real-IP, CF-Connecting-IP) are only
// trusted when running on Vercel, when explicitly enabled via TRUST_PROXY=true,
// or in non-production environments (NODE_ENV=development|test).
// On self-hosted deployments without a trusted reverse proxy, these headers can be
// spoofed by attackers to bypass rate limits.

/**
 * Check if we should trust proxy headers for IP extraction.
 *
 * Returns true when:
 * - Running on Vercel (VERCEL=1) - Vercel always strips/overwrites these headers
 * - Explicitly configured (TRUST_PROXY=true) - for reverse proxy setups
 * - Running in development/test (NODE_ENV=development|test) - keeps local/CI behavior
 *
 * SECURITY: In production on self-hosted deployments, do not trust proxy headers
 * unless your reverse proxy strips inbound values and sets them from the actual
 * client connection (set TRUST_PROXY=true once configured).
 */
function shouldTrustProxyHeaders(): boolean {
  if (process.env.VERCEL === "1" || process.env.TRUST_PROXY === "true") {
    return true;
  }

  const nodeEnv = process.env.NODE_ENV;
  return nodeEnv === "development" || nodeEnv === "test";
}

/**
 * Validate a string as an IPv4 or IPv6 address.
 *
 * Note: This is intentionally strict to avoid treating arbitrary strings from
 * spoofed headers as a "client IP" for security-sensitive operations.
 */
function isValidIpAddress(ip: string): boolean {
  const ipv4Regex =
    /^(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)$/;

  // IPv6 regex supports full, compressed, and IPv4-mapped forms.
  const ipv6Regex =
    /^(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+|::(?:ffff(?::0{1,4})?:)?(?:(?:25[0-5]|(?:2[0-4]|1?\d)?\d)\.){3}(?:25[0-5]|(?:2[0-4]|1?\d)?\d)|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1?\d)?\d)\.){3}(?:25[0-5]|(?:2[0-4]|1?\d)?\d))$/;

  return ipv4Regex.test(ip) || ipv6Regex.test(ip);
}

/**
 * Extract the client IP from trusted sources with deterministic fallback.
 *
 * SECURITY: Proxy headers are only trusted on Vercel, when explicitly configured
 * (TRUST_PROXY=true), or in non-production environments (NODE_ENV=development|test).
 * On untrusted deployments, attackers could spoof these headers to bypass rate limits.
 *
 * Priority order (when proxy headers are trusted):
 * 1) `x-real-ip` (Vercel's canonical client IP header)
 * 2) `x-forwarded-for` (first IP)
 * 3) `cf-connecting-ip` (Cloudflare deployments)
 * 4) `"unknown"`
 *
 * When proxy headers are NOT trusted:
 * - Returns `"unknown"` to ensure consistent rate limiting behavior
 */
export function getClientIpFromHeaders(headers: Pick<Headers, "get">): string {
  // Only trust proxy headers in known environments
  if (!shouldTrustProxyHeaders()) {
    return "unknown";
  }

  const realIp = headers.get("x-real-ip")?.trim();
  if (realIp && isValidIpAddress(realIp)) {
    return realIp;
  }

  const forwardedFor = headers.get("x-forwarded-for");
  if (forwardedFor) {
    const first = forwardedFor.split(",")[0]?.trim();
    if (first && isValidIpAddress(first)) {
      return first;
    }
  }

  const cfIp = headers.get("cf-connecting-ip")?.trim();
  if (cfIp && isValidIpAddress(cfIp)) {
    return cfIp;
  }

  return "unknown";
}
