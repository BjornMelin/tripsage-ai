/** @vitest-environment jsdom */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { fireEvent, render, screen, waitFor } from "@/test/test-utils";

const { mockRecordClientErrorOnActiveSpan } = vi.hoisted(() => ({
  mockRecordClientErrorOnActiveSpan: vi.fn(),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
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
    vi.restoreAllMocks();
  });

  it("renders the password reset request form", () => {
    render(<ResetPasswordForm />);

    expect(
      screen.getByRole("heading", { name: /reset your password/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Email Address")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /send reset instructions/i })
    ).toBeInTheDocument();
  });

  it("reports malformed response payloads through telemetry and shows fallback error text", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify("unexpected response"), {
        headers: { "content-type": "application/json" },
        status: 500,
        statusText: "Internal Server Error",
      })
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
          issueCount: expect.any(Number),
          reason: "schema",
          status: 500,
        }
      );
    });
  });

  it("reports non-JSON responses through telemetry and aborts processing", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("not json", {
        headers: { "content-type": "text/plain" },
        status: 502,
        statusText: "Bad Gateway",
      })
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
});
