/** @vitest-environment jsdom */

import { act } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { server } from "@/test/msw/server";
import { fireEvent, render, screen, waitFor } from "@/test/test-utils";
import { createFakeTimersContext } from "@/test/utils/with-fake-timers";

const { mockRecordClientErrorOnActiveSpan, mockRouterReplace } = vi.hoisted(() => ({
  mockRecordClientErrorOnActiveSpan: vi.fn(),
  mockRouterReplace: vi.fn(),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockRouterReplace,
  }),
}));

function GetResetPasswordForm(): HTMLFormElement {
  const submitButton = screen.getByRole("button", {
    name: /send reset instructions/i,
  });
  const form = submitButton.closest("form");
  if (!form) {
    throw new Error("Expected reset password form to be present");
  }
  return form;
}

describe("ResetPasswordForm", () => {
  beforeEach(() => {
    mockRecordClientErrorOnActiveSpan.mockReset();
    mockRouterReplace.mockReset();
    vi.restoreAllMocks();
  });

  it("renders the password reset request form", () => {
    render(<ResetPasswordForm />);

    expect(
      screen.getByRole("heading", { name: /reset your password/i })
    ).toBeInTheDocument();
    const emailInput = screen.getByLabelText("Email Address");
    expect(emailInput).toBeInTheDocument();
    expect(emailInput).toHaveAccessibleDescription(
      /we'll send password reset instructions/i
    );
    expect(emailInput).not.toHaveAttribute("aria-invalid");
    expect(
      screen.getByRole("button", { name: /send reset instructions/i })
    ).toBeInTheDocument();
  });

  it("reports malformed response payloads through telemetry and shows fallback error text", async () => {
    server.use(
      http.post("/auth/password/reset-request", () =>
        HttpResponse.json("unexpected response", {
          status: 500,
          statusText: "Internal Server Error",
        })
      )
    );

    render(<ResetPasswordForm />);

    fireEvent.change(screen.getByLabelText("Email Address"), {
      target: { value: "traveler@example.com" },
    });
    fireEvent.submit(GetResetPasswordForm());

    const emailInput = screen.getByLabelText("Email Address");
    expect(await screen.findByText("Failed to send reset email")).toBeInTheDocument();
    expect(emailInput).toHaveAttribute("aria-invalid", "true");
    expect(emailInput).toHaveAccessibleDescription(
      /we'll send password reset instructions.*failed to send reset email/i
    );
    await waitFor(() => {
      expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(
        expect.any(Error),
        {
          action: "parseResetResponse",
          context: "ResetPasswordForm",
          issueCount: expect.any(Number),
          reason: "schema",
          status: 500,
        }
      );
    });
  });

  it("reports non-JSON responses through telemetry and aborts processing", async () => {
    server.use(
      http.post("/auth/password/reset-request", () =>
        HttpResponse.text("not json", {
          status: 502,
          statusText: "Bad Gateway",
        })
      )
    );

    render(<ResetPasswordForm />);

    fireEvent.change(screen.getByLabelText("Email Address"), {
      target: { value: "traveler@example.com" },
    });
    fireEvent.submit(GetResetPasswordForm());

    expect(await screen.findByText("Failed to send reset email")).toBeInTheDocument();
    await waitFor(() => {
      expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(
        expect.any(Error),
        {
          action: "parseResetResponse",
          context: "ResetPasswordForm",
          issueCount: 1,
          reason: "json",
          status: 502,
        }
      );
    });
  });

  describe("success redirect", () => {
    const timers = createFakeTimersContext({ shouldAdvanceTime: true });

    beforeEach(timers.setup);
    afterEach(timers.teardown);

    it("uses router navigation after showing success feedback", async () => {
      render(<ResetPasswordForm />);

      fireEvent.change(screen.getByLabelText("Email Address"), {
        target: { value: "traveler@example.com" },
      });
      fireEvent.submit(GetResetPasswordForm());

      expect(
        await screen.findByText(
          "Password reset instructions have been sent to your email"
        )
      ).toBeInTheDocument();
      expect(screen.getByRole("status")).toHaveTextContent(
        "Password reset instructions have been sent to your email"
      );
      expect(mockRouterReplace).not.toHaveBeenCalled();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(mockRouterReplace).toHaveBeenCalledWith("/login");
    });
  });
});
