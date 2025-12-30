/**
 * @fileoverview Shared constants for the `rehype-harden` test mock.
 *
 * Keep these values aligned with the upstream library defaults to ensure test
 * expectations match production hardening behavior.
 */

export const SAFE_PROTOCOLS = new Set([
  "https:",
  "http:",
  "irc:",
  "ircs:",
  "mailto:",
  "xmpp:",
  "blob:",
]);

export const BLOCKED_PROTOCOLS = new Set([
  "javascript:",
  "data:",
  "file:",
  "vbscript:",
]);

// Test sentinel used to exercise blob URL rejection paths in the mock.
export const INVALID_BLOB_MARKER = "invalid";
