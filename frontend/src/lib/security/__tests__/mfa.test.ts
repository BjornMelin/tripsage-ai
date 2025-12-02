/** @vitest-environment node */

import { createHash } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createBackupCodes,
  InvalidBackupCodeError,
  resetBackupCodePepperForTest,
  startTotpEnrollment,
  verifyBackupCode,
  verifyTotp,
} from "@/lib/security/mfa";

const mockIds = {
  challengeId: "22222222-2222-4222-8222-222222222222",
  factorId: "11111111-1111-4111-8111-111111111111",
  userId: "00000000-0000-4000-8000-000000000001",
};

const mfaEnrollmentRows: {
  // biome-ignore lint/style/useNamingConvention: mimic DB columns
  challenge_id: string;
  // biome-ignore lint/style/useNamingConvention: mimic DB columns
  expires_at: string;
  // biome-ignore lint/style/useNamingConvention: mimic DB columns
  factor_id: string;
  // biome-ignore lint/style/useNamingConvention: mimic DB columns
  issued_at: string;
  status: string;
}[] = [];

const mockSupabase = {
  auth: {
    getUser: vi.fn(async () => ({
      data: { user: { id: mockIds.userId } },
      error: null,
    })),
    mfa: {
      challenge: vi.fn(async () => ({
        data: { id: mockIds.challengeId },
        error: null,
      })),
      enroll: vi.fn(async () => ({
        data: {
          id: mockIds.factorId,
          totp: { qr_code: "qr", secret: "secret", uri: "otpauth://..." },
        },
        error: null,
      })),
      verify: vi.fn(async () => ({ data: {}, error: null })),
    },
  },
  from: vi.fn((table: string) => {
    if (table === "mfa_enrollments") {
      return {
        insert: (row: (typeof mfaEnrollmentRows)[number]) => {
          mfaEnrollmentRows.push(row);
          return { error: null };
        },
        select: (_columns: string) => {
          const chain = {
            eq(field: string, value: string) {
              this.filters.push((row) => (row as never)[field] === value);
              return this;
            },
            filters: [] as Array<(row: (typeof mfaEnrollmentRows)[number]) => boolean>,
            order: (_field: string, _opts: { ascending: boolean }) => {
              return {
                limit: (_n: number) => {
                  return {
                    maybeSingle: () => {
                      const filtered = mfaEnrollmentRows.filter((r) =>
                        chain.filters.every((f) => f(r))
                      );
                      const sorted = filtered.sort((a, b) =>
                        b.issued_at.localeCompare(a.issued_at)
                      );
                      const row = sorted[0] || null;
                      return { data: row, error: null };
                    },
                  };
                },
              };
            },
          };
          return chain;
        },
        update: (_values: { status?: string; consumedAt?: string }) => {
          const updateChain = {
            eq: (_field: string, _value: string) => updateChain,
            lt: (_field: string, _value: string) => ({ error: null }),
          };
          return updateChain;
        },
      };
    }
    throw new Error(`Unhandled mock table: ${table}`);
  }),
} as unknown as Parameters<typeof startTotpEnrollment>[0];
const backupRows: {
  // biome-ignore lint/style/useNamingConvention: mimic DB columns
  code_hash: string;
  // biome-ignore lint/style/useNamingConvention: mimic DB columns
  consumed_at: string | null;
  id: string;
  // biome-ignore lint/style/useNamingConvention: mimic DB columns
  user_id: string;
}[] = [];

const mockAdmin = {
  from: vi.fn((table: string) => {
    if (table === "auth_backup_codes") {
      return {
        delete: () => {
          const state = { userId: "" } as { userId: string };
          return {
            eq(field: string, value: string) {
              if (field === "user_id") {
                state.userId = value;
              }
              return {
                not(_field: string, _op: string, inList: string) {
                  const ids = inList
                    .replace(/[()]/g, "")
                    .split(",")
                    .filter(Boolean)
                    .map((id) => id.replace(/"/g, ""));
                  const next = backupRows.filter(
                    (row) => row.user_id !== state.userId || ids.includes(row.id)
                  );
                  backupRows.splice(0, backupRows.length, ...next);
                  return { error: null };
                },
              };
            },
          };
        },
        insert: (rows: typeof backupRows) => {
          const enriched = rows.map((row) => ({
            ...row,
            consumed_at: null,
            id: row.code_hash,
          }));
          backupRows.push(...enriched);
          return {
            select: () => ({ data: enriched.map(({ id }) => ({ id })), error: null }),
          };
        },
        select: (_columns: string, opts?: { count?: string; head?: boolean }) => {
          const filters: Array<(row: (typeof backupRows)[number]) => boolean> = [];
          const chain = {
            eq(field: string, value: string) {
              filters.push((row) => (row as never)[field] === value);
              return chain;
            },
            is(field: string, value: null) {
              filters.push((row) => (row as never)[field] === value);
              if (opts?.head) {
                const count = backupRows.filter((r) =>
                  filters.every((f) => f(r))
                ).length;
                return { count, error: null };
              }
              return chain;
            },
            maybeSingle() {
              const row = backupRows.find((r) => filters.every((f) => f(r)));
              return { data: row ? { id: row.id } : null, error: null };
            },
          };
          return chain;
        },
        update: (values: {
          // biome-ignore lint/style/useNamingConvention: mimic DB columns
          consumed_at: string;
        }) => {
          const filters: Array<(row: (typeof backupRows)[number]) => boolean> = [];
          const chain = {
            eq(field: string, value: string) {
              filters.push((row) => (row as never)[field] === value);
              return chain;
            },
            is(field: string, value: string | null) {
              filters.push((row) => (row as never)[field] === value);
              return chain;
            },
            select: (_cols: string, opts?: { count?: string; head?: boolean }) => {
              const matching = backupRows.filter((row) => filters.every((f) => f(row)));
              matching.forEach((row) => {
                Object.assign(row, values);
              });
              if (opts?.head) {
                return { count: matching.length, error: null };
              }
              return { data: matching, error: null };
            },
          };
          return chain;
        },
      };
    }

    if (table === "mfa_backup_code_audit") {
      return {
        insert: (rows: unknown) => ({ data: rows, error: null }),
      } as unknown as ReturnType<typeof mockAdmin.from>;
    }

    if (table === "mfa_enrollments") {
      return {
        insert: (row: (typeof mfaEnrollmentRows)[number]) => {
          mfaEnrollmentRows.push(row);
          return { error: null };
        },
        update: (values: Partial<(typeof mfaEnrollmentRows)[number]>) => {
          const filters: Array<(row: (typeof mfaEnrollmentRows)[number]) => boolean> =
            [];
          const chain = {
            eq(field: string, value: string) {
              filters.push((row) => (row as never)[field] === value);
              return chain;
            },
            lt: (_field: string, _value: string) => {
              mfaEnrollmentRows.forEach((row) => {
                if (filters.every((f) => f(row))) {
                  Object.assign(row, values);
                }
              });
              return { error: null };
            },
          };
          return chain;
        },
      };
    }

    throw new Error(`Unhandled mock table: ${table}`);
  }),
  rpc: vi.fn((_fn: string, params: Record<string, unknown>) => {
    const hashes = (params.p_code_hashes as string[]) ?? [];
    const userId = params.p_user_id as string;
    backupRows.length = 0;
    backupRows.push(
      ...hashes.map((codeHash) => ({
        code_hash: codeHash,
        consumed_at: null,
        id: codeHash,
        user_id: userId,
      }))
    );
    return { data: hashes.length, error: null };
  }),
} as unknown as Parameters<typeof createBackupCodes>[0];

describe("mfa service", () => {
  beforeEach(() => {
    backupRows.length = 0;
    mfaEnrollmentRows.length = 0;
    process.env.MFA_BACKUP_CODE_PEPPER = "test-pepper-secret-12345";
    resetBackupCodePepperForTest();
    vi.clearAllMocks();
  });

  it("enrolls totp and returns challenge data", async () => {
    const result = await startTotpEnrollment(mockSupabase, {
      adminSupabase: mockAdmin,
    });
    expect(result.factorId).toBe(mockIds.factorId);
    expect(result.challengeId).toBe(mockIds.challengeId);
    expect(result.qrCode).toBe("qr");
  });

  it("verifies totp code during initial enrollment", async () => {
    // Set up pending enrollment data
    mfaEnrollmentRows.push({
      challenge_id: mockIds.challengeId,
      expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      factor_id: mockIds.factorId,
      issued_at: new Date().toISOString(),
      status: "pending",
    });

    const result = await verifyTotp(
      mockSupabase,
      {
        challengeId: mockIds.challengeId,
        code: "123456",
        factorId: mockIds.factorId,
      },
      { adminSupabase: mockAdmin }
    );
    expect(result.isInitialEnrollment).toBe(true);
  });

  it("verifies totp code during subsequent challenge (no enrollment)", async () => {
    // No pending enrollment - simulates regular MFA login challenge
    const result = await verifyTotp(
      mockSupabase,
      {
        challengeId: mockIds.challengeId,
        code: "123456",
        factorId: mockIds.factorId,
      },
      { adminSupabase: mockAdmin }
    );
    expect(result.isInitialEnrollment).toBe(false);
  });

  it("creates backup codes and stores hashed values", async () => {
    const result = await createBackupCodes(mockAdmin, mockIds.userId, 3);
    expect(result.codes).toHaveLength(3);
    expect(result.remaining).toBe(3);
    expect(backupRows).toHaveLength(3);
    expect(mockAdmin.rpc).toHaveBeenCalledWith("replace_backup_codes", {
      p_code_hashes: expect.any(Array),
      p_user_id: mockIds.userId,
    });
  });

  it("rejects invalid backup codes", async () => {
    await expect(
      verifyBackupCode(mockAdmin, mockIds.userId, "AAAAA-BBBBB")
    ).rejects.toBeInstanceOf(InvalidBackupCodeError);
  });

  it("consumes a valid backup code and tracks remaining", async () => {
    const generated = await createBackupCodes(mockAdmin, mockIds.userId, 1);
    const [code] = generated.codes;
    const lookupHash = createHash("sha256")
      .update(`${process.env.MFA_BACKUP_CODE_PEPPER}:${code}`, "utf8")
      .digest("hex");

    const result = await verifyBackupCode(mockAdmin, mockIds.userId, code);
    expect(result.remaining).toBeGreaterThanOrEqual(0);
    const consumed = backupRows.find((r) => r.code_hash === lookupHash);
    expect(consumed?.consumed_at).not.toBeNull();
  });
});
