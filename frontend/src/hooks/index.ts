/**
 * @fileoverview Central export barrel for React hooks. Prefer importing
 * from this module to keep paths stable across refactors.
 */

export * from "./use-accommodation-search";
export * from "./use-activity-search";
export * from "./use-agent-status";
export * from "./use-agent-status-websocket";
// Legacy hooks (to be migrated)
export * from "./use-api-query";
// Modern API hooks
export * from "./use-authenticated-api";
export * from "./use-budget";
export * from "./use-currency";
export * from "./use-deals";
export * from "./use-destination-search";
export * from "./use-error-handler";
export * from "./use-loading";
export * from "./use-memory";
export * from "./use-optimistic-chat";
export * from "./use-search";
export * from "./use-supabase-chat";
// Supabase hooks
export * from "./use-supabase-query";
export * from "./use-supabase-realtime";
export * from "./use-supabase-storage";
export * from "./use-trips";
export * from "./use-trips-with-realtime";
// WebSocket hooks
// WebSocket hooks removed in favor of Supabase Realtime
export * from "./use-websocket-chat";
