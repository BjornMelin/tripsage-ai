/** @vitest-environment node */

import type { Activity } from "@schemas/search";
import { describe, expect, it } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import {
  AI_FALLBACK_PREFIX,
  isActivity,
  partitionActivitiesByFallback,
} from "../activity-results";

const activity = (id: string): Activity =>
  unsafeCast<Activity>({
    id,
    name: `Activity ${id}`,
  });

describe("activity results helpers", () => {
  describe("isActivity", () => {
    it("detects activity-like objects", () => {
      expect(isActivity(null)).toBe(false);
      expect(isActivity({})).toBe(false);
      expect(isActivity({ id: "a" })).toBe(false);
      expect(isActivity({ id: "a", name: "x" })).toBe(true);
    });
  });

  describe("partitionActivitiesByFallback", () => {
    it("returns allAi for fallback-only results", () => {
      const items = [
        activity(`${AI_FALLBACK_PREFIX}1`),
        activity(`${AI_FALLBACK_PREFIX}2`),
      ];
      expect(partitionActivitiesByFallback(items)).toEqual({
        aiSuggestions: items,
        allAi: true,
        verifiedActivities: [],
      });
    });

    it("splits mixed results", () => {
      const verified = activity("v1");
      const ai = activity(`${AI_FALLBACK_PREFIX}a1`);
      const { aiSuggestions, allAi, verifiedActivities } =
        partitionActivitiesByFallback([verified, ai]);
      expect(allAi).toBe(false);
      expect(aiSuggestions).toEqual([ai]);
      expect(verifiedActivities).toEqual([verified]);
    });

    it("returns verified-only when no fallback exists", () => {
      const items = [activity("v1"), activity("v2")];
      expect(partitionActivitiesByFallback(items)).toEqual({
        aiSuggestions: [],
        allAi: false,
        verifiedActivities: items,
      });
    });
  });
});
