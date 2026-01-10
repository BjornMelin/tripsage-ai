/**
 * @fileoverview Shared BotID client-side protection rules.
 */

export type BotIdProtectRule = {
  /**
   * Path pattern to protect. Supports `*` wildcards.
   *
   * Examples:
   * - `/api/chat*` matches `/api/chat` and `/api/chat/sessions/123/messages`
   * - `/team/*` + `/activate` matches `/team/abc/activate`
   */
  path: string;
  /**
   * HTTP method to protect. Supports `*` for all methods.
   */
  method: string;
  advancedOptions?: {
    checkLevel?: "deepAnalysis" | "basic";
  };
};

const BOTID_PROTECT_BASE: BotIdProtectRule[] = [
  // High-value AI endpoints
  { method: "*", path: "/api/chat*" },
  { method: "*", path: "/api/agents*" },
  { method: "*", path: "/api/rag*" },
  { method: "*", path: "/api/ai/stream" },

  // Sensitive API surfaces (BYOK, auth, uploads)
  { method: "*", path: "/api/keys*" },
  { method: "*", path: "/api/auth*" },
  { method: "*", path: "/api/attachments*" },

  // Third-party quota-bearing proxies
  { method: "*", path: "/api/places*" },
  { method: "*", path: "/api/geocode" },
  { method: "*", path: "/api/routes" },
  { method: "*", path: "/api/route-matrix" },
  { method: "*", path: "/api/timezone" },

  // High-value form submissions (Server Actions / non-API routes)
  { method: "POST", path: "/login" },
  { method: "POST", path: "/register" },
  { method: "POST", path: "/auth/password/reset-request" },
];

function normalizeBasePath(value: string | undefined): string {
  const trimmed = value?.trim() ?? "";
  if (!trimmed || trimmed === "/") return "";
  const normalized = trimmed.replace(/^\/+|\/+$/g, "");
  return normalized ? `/${normalized}` : "";
}

/**
 * Resolve BotID protection rules, accounting for Next.js `basePath` when configured.
 *
 * BotID matches against `location.pathname` (no query string). When `NEXT_PUBLIC_BASE_PATH`
 * is set, we must prefix protected routes accordingly so the client adds BotID headers.
 */
export function getBotIdProtectRules(): BotIdProtectRule[] {
  const basePath = normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH);
  if (!basePath) return BOTID_PROTECT_BASE;

  return BOTID_PROTECT_BASE.map((rule) => ({
    ...rule,
    path: `${basePath}${rule.path}`,
  }));
}
