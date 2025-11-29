/**
 * @fileoverview Shared AI tool types for registry-aware agents.
 * Keep minimal to avoid leaking schema module exports.
 */

import type { Tool } from "ai";

/** Canonical AI tool contract used across registry-aware agents. */
export type AiTool = Tool<unknown, unknown>;
