/** @vitest-environment jsdom */

import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { render, screen, waitFor } from "@/test/test-utils";
import { MfaPanel } from "../mfa-panel";

const START_MFA_ENROLLMENT = vi.hoisted(() => vi.fn());
const VERIFY_MFA_TOTP = vi.hoisted(() => vi.fn());
const VERIFY_MFA_BACKUP = vi.hoisted(() => vi.fn());
const REGENERATE_MFA_BACKUPS = vi.hoisted(() => vi.fn());
const REVOKE_OTHER_SESSIONS = vi.hoisted(() => vi.fn());
const REFRESH_MFA_FACTORS = vi.hoisted(() => vi.fn());

vi.mock("@/lib/security/mfa-client", () => ({
  refreshMfaFactors: REFRESH_MFA_FACTORS,
  regenerateMfaBackups: REGENERATE_MFA_BACKUPS,
  resendMfaChallenge: vi.fn(),
  revokeOtherSessions: REVOKE_OTHER_SESSIONS,
  startMfaEnrollment: START_MFA_ENROLLMENT,
  verifyMfaBackup: VERIFY_MFA_BACKUP,
  verifyMfaTotp: VERIFY_MFA_TOTP,
}));

describe("MfaPanel", () => {
  const originalConfirm = global.confirm;

  beforeEach(() => {
    vi.clearAllMocks();
    global.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    global.confirm = originalConfirm;
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
    START_MFA_ENROLLMENT.mockResolvedValueOnce({
      challengeId: "challenge-1",
      factorId: "factor-1",
      qrCode: "data:image/png;base64,TEST",
    });

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );

    await waitFor(() => {
      expect(screen.getByAltText("TOTP QR code")).toBeInTheDocument();
    });
    expect(START_MFA_ENROLLMENT).toHaveBeenCalledTimes(1);
  });

  it("verifies totp code and shows backup codes", async () => {
    START_MFA_ENROLLMENT.mockResolvedValueOnce({
      challengeId: "challenge-1",
      factorId: "factor-1",
      qrCode: "data:image/png;base64,TEST",
    });
    VERIFY_MFA_TOTP.mockResolvedValueOnce({
      aal: "aal2",
      backupCodes: ["ABCDE-12345"],
      factors: [
        { friendlyName: "Main", id: "factor-1", status: "verified", type: "totp" },
      ],
      status: "verified",
    });

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );
    await waitFor(() => {
      expect(screen.getByAltText("TOTP QR code")).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/6-digit code/i, { selector: "input" });
    await userEvent.type(input, "123456");
    await userEvent.click(screen.getByRole("button", { name: /Verify & Enable/i }));

    await waitFor(() => {
      expect(screen.getAllByText(/Enabled/i).length).toBeGreaterThan(0);
    });
    expect(screen.getByText("ABCDE-12345")).toBeInTheDocument();
    expect(VERIFY_MFA_TOTP).toHaveBeenCalledWith({
      challengeId: "challenge-1",
      code: "123456",
      factorId: "factor-1",
    });
  });

  it("accepts backup code", async () => {
    VERIFY_MFA_BACKUP.mockResolvedValueOnce({ remaining: 9 });

    render(<MfaPanel factors={[]} initialAal="aal2" userEmail="test@example.com" />);

    const backupInput = screen.getByLabelText(/backup code/i);
    await userEvent.type(backupInput, "ABCDE-12345");
    await userEvent.click(screen.getByRole("button", { name: /Verify Backup Code/i }));

    await waitFor(() => {
      expect(screen.getByText(/Backup code accepted/i)).toBeInTheDocument();
    });
    expect(VERIFY_MFA_BACKUP).toHaveBeenCalledWith("ABCDE-12345");
  });

  it("handles enrollment failure gracefully", async () => {
    START_MFA_ENROLLMENT.mockRejectedValueOnce(new Error("rate_limited"));

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );

    await waitFor(() => {
      expect(screen.getByText(/rate_limited/i)).toBeInTheDocument();
    });
  });

  it("surfaces network errors during verification", async () => {
    START_MFA_ENROLLMENT.mockResolvedValueOnce({
      challengeId: "challenge-1",
      factorId: "factor-1",
      qrCode: "data:image/png;base64,TEST",
    });
    VERIFY_MFA_TOTP.mockRejectedValueOnce(new Error("network_failure"));

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Start TOTP enrollment/i })
    );
    await waitFor(() => {
      expect(screen.getByAltText("TOTP QR code")).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/6-digit code/i, { selector: "input" });
    await userEvent.type(input, "123456");
    await userEvent.click(screen.getByRole("button", { name: /Verify & Enable/i }));

    await waitFor(() => {
      expect(screen.getByText(/network_failure/i)).toBeInTheDocument();
    });
  });

  it("revokes other sessions", async () => {
    REVOKE_OTHER_SESSIONS.mockResolvedValueOnce(undefined);

    render(<MfaPanel factors={[]} initialAal="aal2" userEmail="test@example.com" />);

    await userEvent.click(
      screen.getByRole("button", { name: /Sign out other sessions/i })
    );

    await waitFor(() => {
      expect(screen.getByText(/Other sessions revoked/i)).toBeInTheDocument();
    });
    expect(REVOKE_OTHER_SESSIONS).toHaveBeenCalledTimes(1);
  });

  it("refreshes factors", async () => {
    REFRESH_MFA_FACTORS.mockResolvedValueOnce({
      aal: "aal2",
      factors: [
        {
          friendlyName: "Key",
          id: "00000000-0000-4000-8000-0000000000f2",
          status: "verified",
          type: "webauthn",
        },
      ],
    });

    render(<MfaPanel factors={[]} initialAal="aal1" userEmail="test@example.com" />);

    await userEvent.click(screen.getByRole("button", { name: /Refresh/i }));

    await waitFor(() => {
      expect(screen.getByText(/Key/)).toBeInTheDocument();
    });
    expect(REFRESH_MFA_FACTORS).toHaveBeenCalledTimes(1);
  });
});
