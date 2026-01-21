/** @vitest-environment node */

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const DIRNAME = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(DIRNAME, "../../../../");

const ROUTES = [
  "src/app/api/activities/search/route.ts",
  "src/app/api/flights/search/route.ts",
  "src/app/api/accommodations/search/route.ts",
];

describe("BotID protection for high-cost public routes", () => {
  for (const routePath of ROUTES) {
    it(`enables botId on ${routePath}`, () => {
      const resolvedPath = resolve(ROOT, routePath);
      const content = readFileSync(resolvedPath, "utf-8");
      expect(content).toContain("botId: true");
    });
  }
});
