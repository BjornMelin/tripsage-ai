/**
 * @fileoverview Vercel AI Gateway base URL validation helpers.
 */

import "server-only";

import { getServerEnvVarWithFallback } from "@/lib/env/server";

const DEFAULT_GATEWAY_HOST = "ai-gateway.vercel.sh";
let cachedAllowedGatewayHosts: Set<string> | null = null;
let cachedAllowedGatewayHostsEnv: string | null = null;

export type GatewayBaseUrlSource = "default" | "team" | "user";

export type GatewayBaseUrlRejectReason =
  | "credentials"
  | "host_not_allowed"
  | "invalid_url"
  | "non_https"
  | "private_host";

export type GatewayBaseUrlValidation =
  | {
      baseUrl?: string;
      host: string;
      ok: true;
      source: GatewayBaseUrlSource;
    }
  | {
      ok: false;
      reason: GatewayBaseUrlRejectReason;
    };

function allowedGatewayHosts(): Set<string> {
  const configured = getServerEnvVarWithFallback("AI_GATEWAY_ALLOWED_HOSTS", "") ?? "";
  if (cachedAllowedGatewayHosts && cachedAllowedGatewayHostsEnv === configured) {
    return cachedAllowedGatewayHosts;
  }

  const hosts = new Set([DEFAULT_GATEWAY_HOST]);
  for (const host of configured.split(",")) {
    const normalized = host.trim().toLowerCase();
    if (normalized) hosts.add(normalized);
  }
  cachedAllowedGatewayHosts = hosts;
  cachedAllowedGatewayHostsEnv = configured;
  return hosts;
}

function isPrivateGatewayHost(hostname: string): boolean {
  const host = hostname.toLowerCase();

  if (host === "localhost") return true;
  if (host.endsWith(".local")) return true;

  const ipv4Match = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/u.exec(host);
  if (ipv4Match) {
    const octets = [
      Number(ipv4Match[1]),
      Number(ipv4Match[2]),
      Number(ipv4Match[3]),
      Number(ipv4Match[4]),
    ];
    if (octets.some((octet) => !Number.isInteger(octet) || octet < 0 || octet > 255)) {
      return true;
    }
    const [a, b] = octets;
    if (a === 0 || a === 10 || a === 127) return true;
    if (a === 169 && b === 254) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 192 && b === 168) return true;
    return false;
  }

  const trimmed = host.replace(/^\[|\]$/gu, "");
  const ipv6 = trimmed.toLowerCase();

  if (ipv6 === "::1") return true;
  if (/^(0{1,4}:){7}0*1$/iu.test(ipv6)) return true;

  const firstHextetMatch = /^([0-9a-f]{1,4}):/iu.exec(ipv6);
  if (firstHextetMatch) {
    const firstHextet = Number.parseInt(firstHextetMatch[1], 16);
    if (firstHextet >= 0xfc00 && firstHextet <= 0xfdff) return true;
  }

  if (ipv6.startsWith("fe80")) return true;

  if (ipv6.includes(".")) {
    const lastSegment = ipv6.split(":").pop() ?? "";
    const embeddedIpv4Match = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/u.exec(
      lastSegment
    );
    if (embeddedIpv4Match) {
      const a = Number(embeddedIpv4Match[1]);
      const b = Number(embeddedIpv4Match[2]);
      return (
        a === 10 ||
        (a === 172 && b >= 16 && b <= 31) ||
        (a === 192 && b === 168) ||
        a === 127 ||
        (a === 169 && b === 254)
      );
    }
  }

  return false;
}

/**
 * Validates a Gateway base URL before using or persisting it.
 *
 * Custom hosts are intentionally allowlisted with `AI_GATEWAY_ALLOWED_HOSTS`
 * so user-owned config cannot turn Gateway calls into arbitrary SSRF probes.
 */
export function validateGatewayBaseUrl(
  rawBaseUrl: string | null | undefined,
  options?: { source?: Exclude<GatewayBaseUrlSource, "default"> }
): GatewayBaseUrlValidation {
  if (!rawBaseUrl?.trim()) {
    return {
      host: DEFAULT_GATEWAY_HOST,
      ok: true,
      source: "default",
    };
  }

  let parsed: URL;
  try {
    parsed = new URL(rawBaseUrl);
  } catch {
    return { ok: false, reason: "invalid_url" };
  }

  if (parsed.protocol !== "https:") return { ok: false, reason: "non_https" };
  if (parsed.username || parsed.password) return { ok: false, reason: "credentials" };
  if (isPrivateGatewayHost(parsed.hostname)) {
    return { ok: false, reason: "private_host" };
  }

  const hostname = parsed.hostname.toLowerCase();
  if (!allowedGatewayHosts().has(hostname)) {
    return { ok: false, reason: "host_not_allowed" };
  }

  return {
    baseUrl: parsed.toString(),
    host: hostname,
    ok: true,
    source: options?.source ?? "user",
  };
}
