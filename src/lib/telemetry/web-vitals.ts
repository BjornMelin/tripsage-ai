/**
 * @fileoverview Shared Web Vitals telemetry constants and route normalization.
 */

import { sanitizePathnameForTelemetry } from "@/lib/telemetry/route-key";

export const WEB_VITALS_ENDPOINT = "/api/telemetry/web-vitals";

export const WEB_VITAL_NAMES = [
  "CLS",
  "FCP",
  "FID",
  "INP",
  "LCP",
  "TTFB",
  "Next.js-hydration",
  "Next.js-route-change-to-render",
  "Next.js-render",
] as const;

export const WEB_VITAL_NAVIGATION_TYPES = [
  "back-forward",
  "back-forward-cache",
  "navigate",
  "prerender",
  "reload",
  "restore",
] as const;

export const WEB_VITAL_RATINGS = ["good", "needs-improvement", "poor"] as const;

export const WEB_VITAL_ROUTE_PATTERN = /^\/[A-Za-z0-9/_:.-]*$/;

export type WebVitalName = (typeof WEB_VITAL_NAMES)[number];

export type WebVitalsReportPayload = {
  delta: number;
  name: string;
  navigationType?: string;
  rating?: (typeof WEB_VITAL_RATINGS)[number];
  route: string;
  value: number;
};

type WebVitalValueLimit = { maximum: number; precision: number };

const DEFAULT_DURATION_LIMIT = { maximum: 120_000, precision: 0 } as const;

const WEB_VITAL_VALUE_LIMITS = new Map<WebVitalName, WebVitalValueLimit>([
  ["CLS", { maximum: 10, precision: 3 }],
  ["FCP", DEFAULT_DURATION_LIMIT],
  ["FID", DEFAULT_DURATION_LIMIT],
  ["INP", DEFAULT_DURATION_LIMIT],
  ["LCP", DEFAULT_DURATION_LIMIT],
  ["Next.js-hydration", DEFAULT_DURATION_LIMIT],
  ["Next.js-render", DEFAULT_DURATION_LIMIT],
  ["Next.js-route-change-to-render", DEFAULT_DURATION_LIMIT],
  ["TTFB", DEFAULT_DURATION_LIMIT],
]);

const KNOWN_WEB_VITAL_ROUTES = new Set([
  "/",
  "/ai-demo",
  "/chat",
  "/contact",
  "/dashboard",
  "/dashboard/agent-status",
  "/dashboard/calendar",
  "/dashboard/demo/realtime",
  "/dashboard/profile",
  "/dashboard/search",
  "/dashboard/search/activities",
  "/dashboard/search/destinations",
  "/dashboard/search/flights",
  "/dashboard/search/flights/results",
  "/dashboard/search/hotels",
  "/dashboard/search/unified",
  "/dashboard/security",
  "/dashboard/settings",
  "/dashboard/trips",
  "/dashboard/trips/:id",
  "/dashboard/trips/:uuid",
  "/dashboard/trips/create",
  "/faq",
  "/login",
  "/privacy",
  "/register",
  "/reset-password",
  "/signup",
  "/terms",
]);

export function normalizeWebVitalsRoute(route: string): string {
  const sanitized = sanitizePathnameForTelemetry(route);
  return KNOWN_WEB_VITAL_ROUTES.has(sanitized) ? sanitized : "/unknown";
}

export function isWebVitalsMetricInRange(name: WebVitalName, value: number): boolean {
  const limit = WEB_VITAL_VALUE_LIMITS.get(name);
  return limit !== undefined && value <= limit.maximum;
}

export function roundWebVitalsMetricValue(name: WebVitalName, value: number): number {
  const precision = WEB_VITAL_VALUE_LIMITS.get(name)?.precision ?? 0;
  if (precision === 0) return Math.round(value);
  const multiplier = 10 ** precision;
  return Math.round(value * multiplier) / multiplier;
}
