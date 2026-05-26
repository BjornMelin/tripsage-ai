/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/test-utils";
import { LoginForm } from "../login-form";

const { mockSignInWithOAuth } = vi.hoisted(() => ({
  mockSignInWithOAuth: vi.fn(),
}));

vi.mock("@/lib/auth/actions", () => ({
  loginWithPasswordAction: vi.fn(),
  verifyMfaAction: vi.fn(),
}));

vi.mock("@/lib/supabase/client", () => ({
  useSupabaseRequired: () => ({
    auth: {
      signInWithOAuth: mockSignInWithOAuth,
    },
  }),
}));

describe("LoginForm", () => {
  it("associates credential fields with the form description", () => {
    render(<LoginForm />);

    expect(screen.getByLabelText("Email")).toHaveAccessibleDescription(
      "Access your TripSage dashboard"
    );
    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription(
      "Access your TripSage dashboard"
    );
  });
});
