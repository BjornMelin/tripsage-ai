/** @vitest-environment node */

import { createPersonalInfoFormSchema, personalInfoFormSchema } from "@schemas/profile";
import { describe, expect, it } from "vitest";

const VALID_PROFILE = {
  displayName: "Alex Traveler",
  firstName: "Alex",
  lastName: "Traveler",
};

describe("profile schemas", () => {
  describe("personalInfoFormSchema", () => {
    const schema = createPersonalInfoFormSchema("2026-05-25T12:00:00.000");

    it("rejects users who have not reached the minimum age birthday", () => {
      expect(
        schema.safeParse({
          ...VALID_PROFILE,
          dateOfBirth: "2013-05-26",
        }).success
      ).toBe(false);
    });

    it("accepts users on the minimum age birthday", () => {
      expect(
        schema.safeParse({
          ...VALID_PROFILE,
          dateOfBirth: "2013-05-25",
        }).success
      ).toBe(true);
    });

    it("rejects users past the maximum age birthday", () => {
      expect(
        schema.safeParse({
          ...VALID_PROFILE,
          dateOfBirth: "1905-05-25",
        }).success
      ).toBe(false);
    });

    it("rejects impossible ISO date values", () => {
      expect(
        schema.safeParse({
          ...VALID_PROFILE,
          dateOfBirth: "2013-02-31",
        }).success
      ).toBe(false);
    });

    it("keeps the default personal info schema available", () => {
      expect(
        personalInfoFormSchema.safeParse({
          ...VALID_PROFILE,
        }).success
      ).toBe(true);
    });
  });
});
