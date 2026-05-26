/** @vitest-environment node */

import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-api-route-errors.mjs");

function runScannerInTempRepo(files: Record<string, string>) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-route-error-scan-"));

  try {
    execFileSync("git", ["init"], { cwd: tempDir, stdio: "ignore" });

    for (const [filePath, contents] of Object.entries(files)) {
      const absolutePath = join(tempDir, filePath);
      mkdirSync(dirname(absolutePath), { recursive: true });
      writeFileSync(absolutePath, contents);
    }

    execFileSync("git", ["add", "."], { cwd: tempDir, stdio: "ignore" });

    return spawnSync(process.execPath, [scriptPath, "--full"], {
      cwd: tempDir,
      encoding: "utf8",
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

describe("check-api-route-errors", () => {
  it("detects legacy code payloads in auth route error responses", () => {
    const result = runScannerInTempRepo({
      "src/app/auth/password/reset/route.ts": `
        import { NextResponse } from "next/server";

        export function POST() {
          return NextResponse.json(
            { code: "RESET_FAILED", message: "Password reset failed" },
            { status: 400 }
          );
        }
      `,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("src/app/auth/password/reset/route.ts");
    expect(result.stderr).toContain("NextResponse.json");
    expect(result.stderr).toContain("authRouteErrorResponse");
  });

  it("detects error payloads in API route error responses", () => {
    const result = runScannerInTempRepo({
      "src/app/api/example/route.ts": `
        import { NextResponse } from "next/server";

        export function GET() {
          return NextResponse.json({ error: "bad_request" }, { status: 400 });
        }
      `,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("src/app/api/example/route.ts");
  });

  it("allows success JSON and shared error helpers in covered routes", () => {
    const result = runScannerInTempRepo({
      "src/app/api/example/route.ts": `
        import { NextResponse } from "next/server";
        import { errorResponse } from "@/lib/api/route-helpers";

        export function GET() {
          if (Math.random() > 2) {
            return errorResponse({
              error: "bad_request",
              reason: "Bad request",
              status: 400,
            });
          }
          return NextResponse.json({ ok: true });
        }
      `,
      "src/app/auth/logout/route.ts": `
        import { NextResponse } from "next/server";
        import { authRouteErrorResponse } from "@/lib/auth/route-error-response";

        export function POST() {
          if (Math.random() > 2) {
            return authRouteErrorResponse({
              error: "logout_failed",
              reason: "signout failed",
              status: 500,
            });
          }
          return NextResponse.json({ success: true });
        }
      `,
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK: no forbidden inline route error responses");
  });

  it("ignores route handlers outside API and auth trees", () => {
    const result = runScannerInTempRepo({
      "src/app/robots/route.ts": `
        import { NextResponse } from "next/server";

        export function GET() {
          return NextResponse.json({ code: "STATIC_ROUTE" }, { status: 400 });
        }
      `,
    });

    expect(result.status).toBe(0);
  });
});
