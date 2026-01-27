/**
 * @fileoverview MSW handlers for Supabase REST API endpoints.
 *
 * Provides default mock responses for Supabase REST API patterns.
 * Prefer module-level mocks or the shared helpers in `src/test/helpers/` when possible.
 * These handlers are for tests that need to mock HTTP-level Supabase interactions.
 */

import { HttpResponse, http } from "msw";
import { TEST_USER_ID } from "@/test/helpers/ids";
import { MSW_FIXED_ISO_DATE, MSW_SUPABASE_URL } from "../constants";

/**
 * Default Supabase handlers providing happy-path responses.
 */
export const supabaseHandlers = [
  // Supabase Auth endpoints
  http.get(`${MSW_SUPABASE_URL}/auth/v1/user`, () => {
    return HttpResponse.json({
      // biome-ignore lint/style/useNamingConvention: match Supabase auth payload
      app_metadata: {},
      // biome-ignore lint/style/useNamingConvention: match Supabase auth payload
      created_at: MSW_FIXED_ISO_DATE,
      email: "test@example.com",
      id: TEST_USER_ID,
      // biome-ignore lint/style/useNamingConvention: match Supabase auth payload
      user_metadata: {},
    });
  }),

  // Supabase REST API - Generic table query pattern
  // This is a catch-all for REST queries - override in specific tests
  http.get(`${MSW_SUPABASE_URL}/rest/v1/:table`, ({ params: _params }) => {
    return HttpResponse.json([]);
  }),

  http.post(`${MSW_SUPABASE_URL}/rest/v1/:table`, ({ params: _params }) => {
    return HttpResponse.json({
      // biome-ignore lint/style/useNamingConvention: match Supabase row payload
      created_at: MSW_FIXED_ISO_DATE,
      id: "mock-id",
    });
  }),

  // Supabase RPC endpoint pattern
  http.post(`${MSW_SUPABASE_URL}/rest/v1/rpc/:function`, ({ params: _params }) => {
    return HttpResponse.json({ success: true });
  }),

  // Supabase Realtime - Channel subscription
  http.post(`${MSW_SUPABASE_URL}/realtime/v1/channels`, () => {
    return HttpResponse.json({
      channel: "mock-channel",
      status: "ok",
    });
  }),
];
