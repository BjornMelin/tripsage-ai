/**
 * @fileoverview Security test for BYOK routes.
 *
 * Ensures BYOK routes maintain security requirements per ADR-0024:
 * - No 'use cache' directives (prevents caching of sensitive API key data)
 * - Security comments documenting Cache Components dynamic behavior
 * - Routes use withApiGuards({ auth: true }) to ensure dynamic execution
 *
 * Reference: docs/adrs/adr-0024-byok-routes-and-security.md
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const BYOK_ROUTE_FILES = [
  "route.ts",
  "[service]/route.ts",
  "validate/route.ts",
] as const;

const BYOK_ROUTES_DIR = join(process.cwd(), "src/app/api/keys");

describe("BYOK Routes Security (ADR-0024)", () => {
  for (const routeFile of BYOK_ROUTE_FILES) {
    it(`should not contain 'use cache' directive in ${routeFile}`, () => {
      const filePath = join(BYOK_ROUTES_DIR, routeFile);
      const content = readFileSync(filePath, "utf-8");

      // CRITICAL: BYOK routes must never cache sensitive API key data
      // Check for actual directive patterns, not comment text
      const hasDirective =
        /['"]use cache['"]\s*[;:]/.test(content) ||
        /['"]use cache:\s*private['"]/.test(content);

      expect(hasDirective).toBe(false);
    });

    it(`should contain security comment referencing ADR-0024 in ${routeFile}`, () => {
      const filePath = join(BYOK_ROUTES_DIR, routeFile);
      const content = readFileSync(filePath, "utf-8");

      // Security comment should reference ADR-0024 or Cache Components dynamic behavior
      const hasSecurityComment =
        content.includes("ADR-0024") ||
        content.includes("Cache Components") ||
        content.includes("dynamic by default");

      expect(hasSecurityComment).toBe(true);
    });

    it(`should use 'server-only' import in ${routeFile}`, () => {
      const filePath = join(BYOK_ROUTES_DIR, routeFile);
      const content = readFileSync(filePath, "utf-8");

      // All BYOK routes must use server-only to prevent client execution
      expect(content).toContain('import "server-only"');
    });

    it(`should use withApiGuards({ auth: true }) in ${routeFile}`, () => {
      const filePath = join(BYOK_ROUTES_DIR, routeFile);
      const content = readFileSync(filePath, "utf-8");

      // BYOK routes must use authentication to ensure dynamic execution
      // This ensures routes use cookies/headers, making them dynamic with Cache Components
      expect(content).toContain("auth: true");
    });
  }
});

describe("User Settings Route Security", () => {
  it("should not contain 'use cache' directive in user-settings/route.ts", () => {
    const filePath = join(process.cwd(), "src/app/api/user-settings/route.ts");
    const content = readFileSync(filePath, "utf-8");

    // User settings route handles user-specific data and should not be cached
    // Check for actual directive patterns, not comment text
    const hasDirective =
      /['"]use cache['"]\s*[;:]/.test(content) ||
      /['"]use cache:\s*private['"]/.test(content);

    expect(hasDirective).toBe(false);
  });

  it("should contain security comment in user-settings/route.ts", () => {
    const filePath = join(process.cwd(), "src/app/api/user-settings/route.ts");
    const content = readFileSync(filePath, "utf-8");

    // Security comment should reference Cache Components or dynamic behavior
    const hasSecurityComment =
      content.includes("Cache Components") ||
      content.includes("dynamic by default") ||
      content.includes("user-specific");

    expect(hasSecurityComment).toBe(true);
  });
});
