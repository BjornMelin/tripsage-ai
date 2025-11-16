/**
 * @fileoverview Central export barrel for React hooks. Prefer importing
 * from this module to keep paths stable across refactors.
 */

/** Re-exports accommodation search hook helpers. */
export * from "./use-accommodation-search";
/** Re-exports activity search hook helpers. */
export * from "./use-activity-search";
/** Re-exports the agent status WebSocket hook. */
export * from "./use-agent-status-websocket";
// Modern API hooks
/** Re-exports the authenticated API hook. */
export * from "./use-authenticated-api";
/** Re-exports budget state hooks. */
export * from "./use-budget";
/** Re-exports currency preference hooks. */
export * from "./use-currency";
/** Re-exports deal discovery hooks. */
export * from "./use-deals";
/** Re-exports destination search hooks. */
export * from "./use-destination-search";
/** Re-exports error handler utilities. */
export * from "./use-error-handler";
/** Re-exports loading state helpers. */
export * from "./use-loading";
/** Re-exports conversational memory hook. */
export * from "./use-memory";
/** Re-exports optimistic chat hook. */
export * from "./use-optimistic-chat";
/** Re-exports search orchestration hook. */
export * from "./use-search";
/** Re-exports Supabase chat hook. */
export * from "./use-supabase-chat";
// Supabase hooks
/** Re-exports Supabase realtime hook. */
export * from "./use-supabase-realtime";
/** Re-exports Supabase storage hook. */
export * from "./use-supabase-storage";
/** Re-exports Trips data hooks. */
export * from "./use-trips";
// WebSocket hooks
// WebSocket hooks removed in favor of Supabase Realtime
/** Re-exports websocket chat hook for legacy consumers. */
export * from "./use-websocket-chat";
