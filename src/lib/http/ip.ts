/**
 * @fileoverview Client IP extraction helpers for server-side requests.
 */

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
 * Priority order:
 * 1) `x-real-ip` (Vercel's canonical client IP header)
 * 2) `x-forwarded-for` (first IP)
 * 3) `cf-connecting-ip` (Cloudflare deployments)
 * 4) `"unknown"`
 */
export function getClientIpFromHeaders(headers: Pick<Headers, "get">): string {
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
