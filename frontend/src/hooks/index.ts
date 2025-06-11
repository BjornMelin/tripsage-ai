// Export all hooks for easy import

// Supabase core hooks
export * from "./use-supabase-query";
export * from "./use-supabase-realtime";

// Trip management hooks (Supabase-powered)
export * from "./use-trips-supabase";

// Chat hooks (Supabase-powered)
export * from "./use-chat-supabase";

// File storage hooks
export * from "./use-file-storage";

// Search hooks (with caching)
export * from "./use-search-supabase";

// Legacy hooks (to be migrated)
export * from "./use-api-query";
export * from "./use-api-keys";
export * from "./use-agent-status";
export * from "./use-search";
export * from "./use-budget";
export * from "./use-currency";
export * from "./use-deals";
export * from "./use-trips";
export * from "./use-memory";
export * from "./use-loading";
export * from "./use-error-handler";
export * from "./use-chat-ai";
export * from "./use-optimistic-chat";
export * from "./use-activity-search";
export * from "./use-accommodation-search";
export * from "./use-destination-search";

// WebSocket hooks
export * from "./use-websocket";
export * from "./use-websocket-chat";
export * from "./use-websocket-agent";
export * from "./use-agent-status-websocket";
