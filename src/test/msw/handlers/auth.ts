/**
 * @fileoverview MSW handlers for authentication endpoints.
 *
 * Provides default mock responses for:
 * - /api/auth/login
 * - /api/auth/register
 * - /api/auth/logout
 * - /api/auth/me
 * - /api/auth/callback
 */

import { HttpResponse, http } from "msw";
import { MSW_FIXED_ISO_DATE } from "../constants";

/**
 * Default auth handlers providing happy-path responses.
 */
export const authHandlers = [
  // GET /api/auth/me - Current user endpoint
  http.get("/api/auth/me", () => {
    return HttpResponse.json({
      user: {
        // biome-ignore lint/style/useNamingConvention: align with Supabase response fields
        created_at: MSW_FIXED_ISO_DATE,
        email: "test@example.com",
        id: "mock-user-id",
      },
    });
  }),

  // POST /api/auth/login - Login endpoint
  http.post("/api/auth/login", () => {
    return HttpResponse.json({
      session: {
        // biome-ignore lint/style/useNamingConvention: align with Supabase response fields
        access_token: "mock-access-token",
        // biome-ignore lint/style/useNamingConvention: align with Supabase response fields
        refresh_token: "mock-refresh-token",
      },
      user: {
        email: "test@example.com",
        id: "mock-user-id",
      },
    });
  }),

  // POST /api/auth/register - Registration endpoint
  http.post("/api/auth/register", () => {
    return HttpResponse.json({
      user: {
        email: "test@example.com",
        id: "mock-user-id",
      },
    });
  }),

  // POST /api/auth/logout - Logout endpoint
  http.post("/api/auth/logout", () => {
    return HttpResponse.json({ success: true });
  }),

  // GET /api/auth/callback - OAuth callback endpoint
  http.get("/api/auth/callback", () => {
    return HttpResponse.redirect("/dashboard");
  }),
];
