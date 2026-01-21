/** @vitest-environment node */

import { createRequire } from "node:module";
import { describe, expect, it } from "vitest";

describe("import-in-the-middle resolution", () => {
  it("resolves import-in-the-middle and require-in-the-middle from the app root", () => {
    const require = createRequire(import.meta.url);
    expect(require.resolve("import-in-the-middle")).toBeTruthy();
    expect(require.resolve("require-in-the-middle")).toBeTruthy();
  });
});
