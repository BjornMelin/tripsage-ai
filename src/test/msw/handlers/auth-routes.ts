/**
 * @fileoverview MSW handlers for app auth routes used in component/store tests.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";
import { createAuthUser } from "@/test/factories/auth-user-factory";

type AuthRouteOptions = {
  user?: ReturnType<typeof createAuthUser>;
};
const buildDefaultUser = (overrides?: AuthRouteOptions["user"]) =>
  createAuthUser(overrides ?? {});

export const createAuthRouteHandlers = (
  options: AuthRouteOptions = {}
): HttpHandler[] => {
  const user = buildDefaultUser(options.user);

  return [
    http.get("/auth/me", () => HttpResponse.json({ user })),

    http.post("/auth/logout", () => HttpResponse.json({ ok: true })),

    http.post("/auth/password/reset-request", async ({ request }) => {
      const body = (await request.json()) as { email?: string };
      if (!body.email) {
        return HttpResponse.json({ message: "Email is required" }, { status: 400 });
      }
      return HttpResponse.json({ ok: true });
    }),

    http.post("/auth/password/reset", () => HttpResponse.json({ ok: true })),

    http.post("/auth/password/change", async ({ request }) => {
      const body = (await request.json()) as {
        currentPassword?: string;
        newPassword?: string;
      };
      if (body.currentPassword === "wrongpassword") {
        return HttpResponse.json(
          { message: "Current password incorrect" },
          { status: 400 }
        );
      }
      return HttpResponse.json({ ok: true });
    }),

    http.post("/auth/email/verify", async ({ request }) => {
      const body = (await request.json()) as { token?: string };
      if (body.token === "invalid-token") {
        return HttpResponse.json({ message: "Invalid token" }, { status: 400 });
      }
      return HttpResponse.json({ ok: true });
    }),

    http.post("/auth/email/resend", () => HttpResponse.json({ ok: true })),
  ];
};

export const authRouteHandlers: HttpHandler[] = createAuthRouteHandlers();
