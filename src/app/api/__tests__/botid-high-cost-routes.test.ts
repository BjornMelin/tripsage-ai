/** @vitest-environment node */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROUTES = [
  "src/app/api/activities/search/route.ts",
  "src/app/api/flights/search/route.ts",
  "src/app/api/accommodations/search/route.ts",
];

describe("BotID protection for high-cost public routes", () => {
  for (const routePath of ROUTES) {
    it(`enables botId on ${routePath}`, () => {
      const content = readFileSync(join(process.cwd(), routePath), "utf-8");
      expect(content).toContain("botId: true");
    });
  }
});
