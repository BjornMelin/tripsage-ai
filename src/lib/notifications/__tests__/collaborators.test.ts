/** @vitest-environment node */

import * as supabaseModule from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { sendCollaboratorNotifications } from "@/lib/notifications/collaborators";

const envValues = vi.hoisted(() => ({
  COLLAB_WEBHOOK_URL: undefined,
  NEXT_PUBLIC_SUPABASE_URL: "https://supabase.test",
  RESEND_API_KEY: "resend-key",
  RESEND_FROM_EMAIL: "noreply@test.dev",
  RESEND_FROM_NAME: "TripSage QA",
  SUPABASE_SERVICE_ROLE_KEY: "service-role",
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (key: string) => {
    const store = envValues as Record<string, string | undefined>;
    const value = store[key];
    if (!value) throw new Error(`Missing env: ${key}`);
    return value;
  },
  getServerEnvVarWithFallback: (key: string, fallback?: string) => {
    const store = envValues as Record<string, string | undefined>;
    const value = store[key];
    return (value ?? fallback) as string;
  },
}));

vi.mock("resend", () => {
  const emailsSend = vi.fn().mockResolvedValue({ id: "email_1" });
  class Resend {
    emails = { send: emailsSend };
  }
  return { Resend };
});

describe("sendCollaboratorNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns empty result when table is not trip_collaborators", async () => {
    const result = await sendCollaboratorNotifications(
      {
        oldRecord: null,
        record: {},
        table: "other_table",
        type: "INSERT",
      },
      "event-key"
    );
    expect(result).toEqual({});
  });

  it("sends email when user email is resolved", async () => {
    const authAdminGetUserById = vi.fn().mockResolvedValue({
      data: { user: { email: "user@example.com" } },
      error: null,
    });
    vi.spyOn(supabaseModule, "createClient").mockReturnValue({
      auth: { admin: { getUserById: authAdminGetUserById } },
    } as unknown as ReturnType<typeof supabaseModule.createClient>);

    const result = await sendCollaboratorNotifications(
      {
        oldRecord: null,
        record: { trip_id: 1, user_id: "user-1" },
        table: "trip_collaborators",
        type: "INSERT",
      },
      "event-key-1"
    );

    expect(result.emailed).toBe(true);
  });
});
