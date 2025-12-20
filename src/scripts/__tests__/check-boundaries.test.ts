/** @vitest-environment node */

import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";

let findDomainViolations: typeof import("../../../scripts/check-boundaries.mjs").findDomainViolations;
let getImportSpecifiers: typeof import("../../../scripts/check-boundaries.mjs").getImportSpecifiers;
let isClientComponent: typeof import("../../../scripts/check-boundaries.mjs").isClientComponent;

beforeAll(async () => {
  ({ findDomainViolations, getImportSpecifiers, isClientComponent } = await import(
    "../../../scripts/check-boundaries.mjs"
  ));
});

describe("check-boundaries helpers", () => {
  it("extracts import specifiers from multiple module syntaxes", () => {
    const content = `
      import { headers } from "next/headers";
      export { foo } from "@/app/api/foo";
      const bar = require("src/app/bar");
      const baz = import("next/cache");
    `;

    const specifiers = getImportSpecifiers(content);
    expect(specifiers).toEqual(
      expect.arrayContaining([
        "next/headers",
        "@/app/api/foo",
        "src/app/bar",
        "next/cache",
      ])
    );
  });

  it("detects domain imports of app and next modules", () => {
    const repoRoot = process.cwd();
    const filePath = path.join(repoRoot, "src/domain/nested/service.ts");
    const specifiers = ["next/headers", "@/app/api/foo", "../../app/api/bar"];

    const { appViolations, nextViolations } = findDomainViolations(
      specifiers,
      filePath,
      repoRoot
    );

    expect(nextViolations).toEqual(["next/headers"]);
    expect(appViolations).toEqual(
      expect.arrayContaining(["@/app/api/foo", "../../app/api/bar"])
    );
  });

  it("detects client components via use client directive", () => {
    expect(isClientComponent('"use client";\nexport const x = 1;')).toBe(true);
    expect(isClientComponent("export const x = 1;")).toBe(false);
  });
});
