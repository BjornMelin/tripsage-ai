/**
 * @fileoverview Bot protection routes for BotId.
 */

import "server-only";

import { getRuntimeEnv } from "@/lib/env/runtime-env";
import { getBotIdEnableCsv } from "@/lib/env/server-flags";

export type HttpMethod =
  | "GET"
  | "POST"
  | "PUT"
  | "PATCH"
  | "DELETE"
  | "OPTIONS"
  | "HEAD";

export type BotIdProtectRule = { method: HttpMethod; path: string };

export const BOTID_PROTECT: BotIdProtectRule[] = [
  { method: "POST", path: "/api/chat/stream" },
  { method: "POST", path: "/api/agents/router" },
  { method: "POST", path: "/api/chat/attachments" },
];

// Default `BOTID_ENABLE` intentionally excludes "development" and "test" so BotId is disabled
// locally and in tests unless overridden.
const BOTID_ENABLE = getBotIdEnableCsv();

// Treat empty `BOTID_ENABLE` the same as undefined (fall back to defaults).
const BOTID_ENABLED_ENVS = new Set(
  BOTID_ENABLE.split(",")
    .map((value) => value.trim())
    .filter(Boolean)
);
export const SHOULD_ENABLE_BOT_ID = BOTID_ENABLED_ENVS.has(getRuntimeEnv());
