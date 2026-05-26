/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/test-utils";
import { RegisterForm } from "../register-form";

const { mockSignInWithOAuth } = vi.hoisted(() => ({
  mockSignInWithOAuth: vi.fn(),
}));

vi.mock("@/lib/auth/actions", () => ({
  registerWithPasswordAction: vi.fn(),
}));

vi.mock("@/lib/supabase/client", () => ({
  useSupabaseRequired: () => ({
    auth: {
      signInWithOAuth: mockSignInWithOAuth,
    },
  }),
}));

describe("RegisterForm", () => {
  it("associates identity and credential fields with the form description", () => {
    render(<RegisterForm />);

    for (const fieldName of [
      "First name",
      "Last name",
      "Email",
      "Password",
      "Confirm password",
    ]) {
      expect(screen.getByLabelText(fieldName)).toHaveAccessibleDescription(
        "Join TripSage to start planning"
      );
    }
  });
});
