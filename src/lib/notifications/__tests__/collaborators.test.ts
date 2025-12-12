/** @vitest-environment node */

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

function createDefaultAuthAdminGetUserByIdResult() {
  return {
    data: { user: { email: "user@example.com" } },
    error: null,
  };
}

const mockAuthAdminGetUserById = vi.hoisted(() =>
  vi.fn().mockResolvedValue(createDefaultAuthAdminGetUserByIdResult())
);

vi.mock("server-only", () => ({}));

vi.mock("@/lib/supabase/admin", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/supabase/admin")>(
      "@/lib/supabase/admin"
    );

  return {
    ...actual,
    createAdminSupabase: (..._args: Parameters<typeof actual.createAdminSupabase>) =>
      ({
        auth: { admin: { getUserById: mockAuthAdminGetUserById } },
      }) as unknown as ReturnType<typeof actual.createAdminSupabase>,
  };
});

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
    mockAuthAdminGetUserById.mockReset();
    mockAuthAdminGetUserById.mockResolvedValue(
      createDefaultAuthAdminGetUserByIdResult()
    );
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
    const result = await sendCollaboratorNotifications(
      {
        oldRecord: null,
        record: { trip_id: 1, user_id: "user-1" },
        table: "trip_collaborators",
        type: "INSERT",
      },
      "event-key-1"
    );

    expect(mockAuthAdminGetUserById).toHaveBeenCalledWith("user-1");
    expect(mockAuthAdminGetUserById).toHaveBeenCalledTimes(1);
    expect(result.emailed).toBe(true);
  });
});
