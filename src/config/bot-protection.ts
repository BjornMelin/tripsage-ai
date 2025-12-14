/**
 * @fileoverview Bot protection routes for BotId.
 */

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
