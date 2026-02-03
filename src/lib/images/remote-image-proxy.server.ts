/**
 * @fileoverview Server-only allowlist and validation utilities for the remote image proxy.
 */

import "server-only";

import { getServerEnvVarWithFallback } from "@/lib/env/server";

function parseAllowedHostsFromEnv(): string[] {
  const raw = getServerEnvVarWithFallback("IMAGE_PROXY_ALLOWED_HOSTS", undefined);
  if (!raw) {
    return [];
  }
  return raw
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter((entry) => entry.length > 0);
}

function normalizeHostname(hostname: string): string {
  return hostname.toLowerCase().replace(/\.$/, "");
}

function isIpAddressHost(hostname: string): boolean {
  const isValidIpv4 = (value: string): boolean => {
    const octets = value.split(".");
    if (octets.length !== 4) return false;
    return octets.every((octet) => {
      if (!/^\d{1,3}$/.test(octet)) return false;
      const numeric = Number(octet);
      return (
        numeric >= 0 && numeric <= 255 && !(octet.length > 1 && octet.startsWith("0"))
      );
    });
  };

  const isValidIpv6 = (value: string): boolean => {
    const trimmed =
      value.startsWith("[") && value.endsWith("]") ? value.slice(1, -1) : value;
    const hexGroup = /^[0-9a-fA-F]{1,4}$/;

    if (trimmed.includes("::")) {
      if (trimmed.indexOf("::") !== trimmed.lastIndexOf("::")) return false;
      const [head, tail] = trimmed.split("::");
      const headGroups = head.length > 0 ? head.split(":") : [];
      const tailGroups = tail.length > 0 ? tail.split(":") : [];
      if (headGroups.length + tailGroups.length >= 8) return false;
      return [...headGroups, ...tailGroups].every((group) => hexGroup.test(group));
    }

    const groups = trimmed.split(":");
    if (groups.length !== 8) return false;
    return groups.every((group) => hexGroup.test(group));
  };

  if (hostname.includes(".")) {
    return isValidIpv4(hostname);
  }
  if (hostname.includes(":")) {
    return isValidIpv6(hostname);
  }
  return false;
}

/**
 * Returns the maximum allowed remote image payload size in bytes.
 *
 * @returns The byte limit used for remote image proxying.
 */
export function getRemoteImageProxyMaxBytes(): number {
  const fallback = 10 * 1024 * 1024;
  const raw = getServerEnvVarWithFallback("IMAGE_PROXY_MAX_BYTES", undefined);
  if (typeof raw !== "number") return fallback;
  if (!Number.isFinite(raw) || raw <= 0) return fallback;
  return Math.min(raw, 25 * 1024 * 1024);
}

/**
 * Determines whether a remote image URL is allowed by the proxy allowlist.
 *
 * @param url - URL to validate.
 * @returns True when the URL is allowed.
 */
export function isAllowedRemoteImageUrl(url: URL): boolean {
  if (url.username || url.password) return false;
  if (url.protocol !== "https:") return false;

  const hostname = normalizeHostname(url.hostname);
  if (hostname === "localhost" || hostname.endsWith(".local")) return false;
  if (isIpAddressHost(hostname)) return false;

  const allowed = parseAllowedHostsFromEnv();
  if (allowed.length === 0) return false;

  return allowed.some((allowedHost) => {
    const normalizedAllowed = normalizeHostname(allowedHost);
    return hostname === normalizedAllowed || hostname.endsWith(`.${normalizedAllowed}`);
  });
}
