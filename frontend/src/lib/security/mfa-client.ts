/**
 * @fileoverview Client-safe MFA API helpers for dashboard UI.
 */

import type {
  BackupCodeRegenerateInput,
  BackupCodeVerifyInput,
  MfaChallengeInput,
  MfaFactor,
  MfaVerificationInput,
} from "@schemas/mfa";

const JSON_HEADERS = { "Content-Type": "application/json" } as const;

/** Basic JSON fetch wrapper that throws on non-2xx with normalized message. */
async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...JSON_HEADERS,
      ...(init?.headers ?? {}),
    },
  });

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  const data = (payload as { data?: T; error?: string } | null) ?? null;

  if (!response.ok || !data?.data) {
    const message = data?.error ?? "unexpected_error";
    const normalizedMessage = response.ok ? message : `${response.status}:${message}`;
    throw new Error(normalizedMessage);
  }

  return data.data;
}

/** Lists MFA factors and current AAL. */
export async function refreshMfaFactors(): Promise<{
  aal: "aal1" | "aal2";
  factors: MfaFactor[];
}> {
  return await fetchJson<{ aal: "aal1" | "aal2"; factors: MfaFactor[] }>(
    "/api/auth/mfa/factors/list",
    { method: "GET" }
  );
}

/** Starts TOTP enrollment and returns QR code + challenge identifiers. */
export async function startMfaEnrollment(): Promise<{
  challengeId: string;
  factorId: string;
  qrCode: string;
}> {
  const enrollment = await fetchJson<{
    challengeId: string;
    factorId: string;
    qrCode: string;
  }>("/api/auth/mfa/setup", { body: "{}", method: "POST" });

  return {
    challengeId: enrollment.challengeId,
    factorId: enrollment.factorId,
    qrCode: enrollment.qrCode,
  };
}

/** Issues a new MFA challenge for an existing factor. */
export async function resendMfaChallenge(input: MfaChallengeInput): Promise<{
  challengeId: string;
}> {
  return await fetchJson<{ challengeId: string }>("/api/auth/mfa/challenge", {
    body: JSON.stringify(input),
    method: "POST",
  });
}

/**
 * Verifies a TOTP MFA code. After a successful verification, refetch factors/AAL
 * to keep the UI state in sync, mirroring the previous server action contract.
 */
export async function verifyMfaTotp(input: MfaVerificationInput): Promise<{
  aal: "aal1" | "aal2";
  backupCodes?: string[];
  factors: MfaFactor[];
  status: "verified";
}> {
  const verification = await fetchJson<{ backupCodes?: string[]; status: "verified" }>(
    "/api/auth/mfa/verify",
    {
      body: JSON.stringify(input),
      method: "POST",
    }
  );

  const { aal, factors } = await refreshMfaFactors();

  return {
    aal,
    backupCodes: verification.backupCodes,
    factors,
    status: "verified",
  };
}

/** Verifies a backup code. */
export async function verifyMfaBackup(code: string): Promise<{ remaining: number }> {
  return await fetchJson<{ remaining: number }>("/api/auth/mfa/backup/verify", {
    body: JSON.stringify({ code } satisfies BackupCodeVerifyInput),
    method: "POST",
  });
}

/** Regenerates backup codes (requires AAL2). */
export async function regenerateMfaBackups(count: number): Promise<{
  backupCodes: string[];
}> {
  return await fetchJson<{ backupCodes: string[] }>("/api/auth/mfa/backup/regenerate", {
    body: JSON.stringify({ count } satisfies BackupCodeRegenerateInput),
    method: "POST",
  });
}

/** Revokes other sessions for the current user. */
export async function revokeOtherSessions(): Promise<void> {
  await fetchJson<{ status: string }>("/api/auth/mfa/sessions/revoke", {
    body: JSON.stringify({ scope: "others" }),
    method: "POST",
  });
}
