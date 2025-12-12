/** @vitest-environment node */

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

  it("should use 'server-only' import in user-settings/route.ts", () => {
    const filePath = join(process.cwd(), "src/app/api/user-settings/route.ts");
    const content = readFileSync(filePath, "utf-8");

    expect(content).toContain('import "server-only"');
  });

  it("should use withApiGuards({ auth: true }) in user-settings/route.ts", () => {
    const filePath = join(process.cwd(), "src/app/api/user-settings/route.ts");
    const content = readFileSync(filePath, "utf-8");

    expect(content).toContain("auth: true");
  });
});
