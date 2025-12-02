/** @vitest-environment jsdom */

import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { render, screen, waitFor } from "@/test/test-utils";
import { MfaPanel } from "../mfa-panel";

describe("MfaPanel", () => {
  const fetchMock = vi.fn();
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    global.fetch = fetchMock;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.clearAllMocks();
  });

  it("renders status and factors", () => {
    render(
      <MfaPanel
        factors={[
          { friendlyName: "Authy", id: "f1", status: "verified", type: "totp" },
        ]}
        initialAal="aal1"
        userEmail="test@example.com"
      />
    );

    expect(screen.getByText(/Not enabled/i)).toBeInTheDocument();
    expect(screen.getByText(/Authy/)).toBeInTheDocument();
  });

  it("starts enrollment and shows QR code", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          data: {
            challengeId: "challenge-1",
            factorId: "factor-1",
            qrCode: "data:image/png;base64,TEST",
          },
        }),
        { status: 200 }
      )
    );

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );

    await waitFor(() =>
      expect(screen.getByAltText("TOTP QR code")).toBeInTheDocument()
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/mfa/setup",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("verifies totp code and shows backup codes", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          data: {
            challengeId: "challenge-1",
            factorId: "factor-1",
            qrCode: "data:image/png;base64,TEST",
          },
        }),
        { status: 200 }
      )
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          data: { backupCodes: ["ABCDE-12345"], status: "verified" },
        }),
        { status: 200 }
      )
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          data: {
            aal: "aal2",
            factors: [
              {
                friendlyName: "Main",
                id: "factor-1",
                status: "verified",
                type: "totp",
              },
            ],
          },
        }),
        { status: 200 }
      )
    );

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );
    await waitFor(() => screen.getByAltText("TOTP QR code"));

    const input = screen.getByLabelText(/6-digit code/i, { selector: "input" });
    await userEvent.type(input, "123456");
    await userEvent.click(screen.getByRole("button", { name: /Verify & Enable/i }));

    await waitFor(() => screen.getByText(/MFA verified/i));
    expect(screen.getByText("ABCDE-12345")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/mfa/verify",
      expect.objectContaining({
        body: JSON.stringify({
          challengeId: "challenge-1",
          code: "123456",
          factorId: "factor-1",
        }),
      })
    );
  });

  it("accepts backup code", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: { remaining: 9 } }), { status: 200 })
    );

    render(<MfaPanel factors={[]} initialAal="aal2" userEmail="test@example.com" />);

    const backupInput = screen.getByLabelText(/backup code/i);
    await userEvent.type(backupInput, "ABCDE-12345");
    await userEvent.click(screen.getByRole("button", { name: /Verify Backup Code/i }));

    await waitFor(() =>
      expect(screen.getByText(/Backup code accepted/i)).toBeInTheDocument()
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/mfa/backup/verify",
      expect.objectContaining({
        body: JSON.stringify({ code: "ABCDE-12345" }),
      })
    );
  });

  it("handles setup API failure gracefully", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "rate_limited" }), { status: 429 })
    );

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );

    await waitFor(() => expect(screen.getByText(/rate_limited/i)).toBeInTheDocument());
  });

  it("surfaces network errors during verification", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              challengeId: "challenge-1",
              factorId: "factor-1",
              qrCode: "data:image/png;base64,TEST",
            },
          }),
          { status: 200 }
        )
      )
      .mockRejectedValueOnce(new Error("network_failure"));

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );
    await waitFor(() => screen.getByAltText("TOTP QR code"));

    const input = screen.getByLabelText(/6-digit code/i, { selector: "input" });
    await userEvent.type(input, "123456");
    await userEvent.click(screen.getByRole("button", { name: /Verify & Enable/i }));

    await waitFor(() =>
      expect(screen.getByText(/network_failure/i)).toBeInTheDocument()
    );
  });

  it("revokes other sessions", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: { status: "revoked" } }), { status: 200 })
    );

    render(<MfaPanel factors={[]} initialAal="aal2" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Sign out other sessions/i })
    );

    await waitFor(() =>
      expect(screen.getByText(/Other sessions revoked/i)).toBeInTheDocument()
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/mfa/sessions/revoke",
      expect.objectContaining({
        body: JSON.stringify({ scope: "others" }),
      })
    );
  });

  it("refreshes factors", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          data: {
            aal: "aal2",
            factors: [
              {
                friendlyName: "Key",
                id: "00000000-0000-4000-8000-0000000000f2",
                status: "verified",
                type: "webauthn",
              },
            ],
          },
        }),
        { status: 200 }
      )
    );

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(screen.getByRole("button", { name: /Refresh/i }));

    await waitFor(() => expect(screen.getByText(/Key/)).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/mfa/factors/list");
  });
});
