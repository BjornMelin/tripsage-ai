/**
 * @fileoverview MSW handlers for Supabase REST API endpoints.
 *
 * Provides default mock responses for Supabase REST API patterns.
 * For most tests, use the type-safe Supabase mock helpers from @/test/mock-helpers.ts
 * These handlers are for tests that need to mock HTTP-level Supabase interactions.
 */

import { HttpResponse, http } from "msw";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "http://localhost:54321";

/**
 * Default Supabase handlers providing happy-path responses.
 */
export const supabaseHandlers = [
  // Supabase Auth endpoints
  http.get(`${SUPABASE_URL}/auth/v1/user`, () => {
    return HttpResponse.json({
      // biome-ignore lint/style/useNamingConvention: match Supabase auth payload
      app_metadata: {},
      // biome-ignore lint/style/useNamingConvention: match Supabase auth payload
      created_at: new Date().toISOString(),
      email: "test@example.com",
      id: "mock-user-id",
      // biome-ignore lint/style/useNamingConvention: match Supabase auth payload
      user_metadata: {},
    });
  }),

  // Supabase REST API - Generic table query pattern
  // This is a catch-all for REST queries - override in specific tests
  http.get(`${SUPABASE_URL}/rest/v1/:table`, ({ params: _params }) => {
    return HttpResponse.json([]);
  }),

  http.post(`${SUPABASE_URL}/rest/v1/:table`, ({ params: _params }) => {
    return HttpResponse.json({
      // biome-ignore lint/style/useNamingConvention: match Supabase row payload
      created_at: new Date().toISOString(),
      id: "mock-id",
    });
  }),

  // Supabase RPC endpoint pattern
  http.post(`${SUPABASE_URL}/rest/v1/rpc/:function`, ({ params: _params }) => {
    return HttpResponse.json({ success: true });
  }),

  // Supabase Realtime - Channel subscription
  http.post(`${SUPABASE_URL}/realtime/v1/channels`, () => {
    return HttpResponse.json({
      channel: "mock-channel",
      status: "ok",
    });
  }),
];
