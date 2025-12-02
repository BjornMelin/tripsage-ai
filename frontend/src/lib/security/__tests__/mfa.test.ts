/** @vitest-environment node */

import { createHash } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createBackupCodes,
  startTotpEnrollment,
  verifyBackupCode,
  verifyTotp,
} from "@/lib/security/mfa";

const mockSupabase = {
  auth: {
    mfa: {
      challenge: vi.fn(async () => ({ data: { id: "challenge-1" }, error: null })),
      enroll: vi.fn(async () => ({
        data: {
          id: "factor-1",
          totp: { qr_code: "qr", secret: "secret", uri: "otpauth://..." },
        },
        error: null,
      })),
      verify: vi.fn(async () => ({ data: {}, error: null })),
    },
  },
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
  from: vi.fn((_table: string) => {
    return {
      delete: () => ({
        eq: () => ({ error: null }),
      }),
      insert: (rows: typeof backupRows) => {
        backupRows.push(
          ...rows.map((row) => ({ ...row, consumed_at: null, id: row.code_hash }))
        );
        return { error: null };
      },
      select: (_columns: string, opts?: { count?: string; head?: boolean }) => {
        const chain = {
          eq(field: string, value: string) {
            this.filters.push((row) => (row as never)[field] === value);
            return this;
          },
          filters: [] as Array<(row: (typeof backupRows)[number]) => boolean>,
          is(field: string, value: null) {
            this.filters.push((row) => (row as never)[field] === value);
            return this;
          },
          maybeSingle() {
            const row = backupRows.find((r) => this.filters.every((f) => f(r)));
            return { data: row ? { id: row.id } : null, error: null };
          },
        };
        if (opts?.head) {
          return {
            eq(field: string, value: string) {
              this.filters.push((row) => (row as never)[field] === value);
              return this;
            },
            filters: [] as Array<(row: (typeof backupRows)[number]) => boolean>,
            is(field: string, value: null) {
              this.filters.push((row) => (row as never)[field] === value);
              const count = backupRows.filter((r) =>
                this.filters.every((f) => f(r))
              ).length;
              return { count, error: null };
            },
          };
        }
        return chain;
      },
      update: (values: {
        // biome-ignore lint/style/useNamingConvention: mimic DB columns
        consumed_at: string;
      }) => ({
        eq: (_field: string, id: string) => {
          const row = backupRows.find((r) => r.id === id);
          if (row) row.consumed_at = values.consumed_at;
          return { error: null };
        },
      }),
    };
  }),
} as unknown as Parameters<typeof createBackupCodes>[0];

let currentLookupHash = "";

describe("mfa service", () => {
  beforeEach(() => {
    backupRows.length = 0;
    currentLookupHash = "";
    vi.clearAllMocks();
  });

  it("enrolls totp and returns challenge data", async () => {
    const result = await startTotpEnrollment(mockSupabase);
    expect(result.factorId).toBe("factor-1");
    expect(result.challengeId).toBe("challenge-1");
    expect(result.qrCode).toBe("qr");
  });

  it("verifies totp code", async () => {
    await expect(
      verifyTotp(mockSupabase, {
        challengeId: "challenge-1",
        code: "123456",
        factorId: "factor-1",
      })
    ).resolves.toBeUndefined();
  });

  it("creates backup codes and stores hashed values", async () => {
    const result = await createBackupCodes(mockAdmin, "user-1", 3);
    expect(result.codes).toHaveLength(3);
    expect(result.remaining).toBe(3);
    expect(backupRows).toHaveLength(3);
  });

  it("rejects invalid backup codes", async () => {
    await expect(
      verifyBackupCode(mockAdmin, "user-1", "AAAAA-BBBBB")
    ).rejects.toThrow();
  });

  it("consumes a valid backup code and tracks remaining", async () => {
    const generated = await createBackupCodes(mockAdmin, "user-1", 1);
    const [code] = generated.codes;
    currentLookupHash = createHash("sha256")
      .update(`mfa-backup-code:${code}`, "utf8")
      .digest("hex");

    const result = await verifyBackupCode(mockAdmin, "user-1", code);
    expect(result.remaining).toBeGreaterThanOrEqual(0);
    const consumed = backupRows.find((r) => r.code_hash === currentLookupHash);
    expect(consumed?.consumed_at).not.toBeNull();
  });
});
