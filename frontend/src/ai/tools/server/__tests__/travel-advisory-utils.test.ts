import {
  extractSafetyCategories,
  htmlToPlainText,
  levelToScore,
  mapToCountryCode,
  parseAdvisoryLevel,
} from "@ai/tools/server/travel-advisory/utils";
import { describe, expect, test } from "vitest";

describe("levelToScore", () => {
  test("converts Level 1 to score 85", () => {
    expect(levelToScore(1)).toBe(85);
  });

  test("converts Level 2 to score 60", () => {
    expect(levelToScore(2)).toBe(60);
  });

  test("converts Level 3 to score 35", () => {
    expect(levelToScore(3)).toBe(35);
  });

  test("converts Level 4 to score 10", () => {
    expect(levelToScore(4)).toBe(10);
  });

  test("returns neutral score for unknown level", () => {
    expect(levelToScore(5)).toBe(50);
    expect(levelToScore(0)).toBe(50);
  });
});

describe("parseAdvisoryLevel", () => {
  test("extracts Level 1 from title", () => {
    expect(parseAdvisoryLevel("Austria - Level 1: Exercise Normal Precautions")).toBe(
      1
    );
  });

  test("extracts Level 2 from title", () => {
    expect(parseAdvisoryLevel("France - Level 2: Exercise Increased Caution")).toBe(2);
  });

  test("extracts Level 3 from title", () => {
    expect(parseAdvisoryLevel("Level 3: Reconsider Travel")).toBe(3);
  });

  test("extracts Level 4 from title", () => {
    expect(parseAdvisoryLevel("Level 4: Do Not Travel")).toBe(4);
  });

  test("returns null for title without level", () => {
    expect(parseAdvisoryLevel("Some Country Travel Advisory")).toBeNull();
  });

  test("handles case-insensitive matching", () => {
    expect(parseAdvisoryLevel("level 1: test")).toBe(1);
    expect(parseAdvisoryLevel("LEVEL 2: TEST")).toBe(2);
  });
});

describe("htmlToPlainText", () => {
  test("strips HTML tags", () => {
    const html = "<p>Hello <b>world</b></p>";
    const result = htmlToPlainText(html);
    expect(result).toBe("Hello world");
  });

  test("preserves line breaks", () => {
    const html = "<p>Line 1</p><p>Line 2</p>";
    const result = htmlToPlainText(html);
    expect(result).toContain("Line 1");
    expect(result).toContain("Line 2");
  });

  test("removes script tags", () => {
    const html = "<p>Text</p><script>alert('xss')</script>";
    const result = htmlToPlainText(html);
    expect(result).not.toContain("alert");
    expect(result).toContain("Text");
  });

  test("handles empty HTML", () => {
    expect(htmlToPlainText("")).toBe("");
    expect(htmlToPlainText("<p></p>")).toBe("");
  });

  test("handles links", () => {
    const html = '<p>Visit <a href="https://example.com">example</a></p>';
    const result = htmlToPlainText(html);
    expect(result).toContain("example");
    expect(result).not.toContain("href");
  });
});

describe("mapToCountryCode", () => {
  test("maps ISO codes directly", () => {
    expect(mapToCountryCode("US")).toBe("US");
    expect(mapToCountryCode("FR")).toBe("FR");
    expect(mapToCountryCode("GB")).toBe("GB");
  });

  test("maps country names to ISO codes", () => {
    expect(mapToCountryCode("United States")).toBe("US");
    expect(mapToCountryCode("France")).toBe("FR");
    expect(mapToCountryCode("United Kingdom")).toBe("GB");
  });

  test("handles case-insensitive input", () => {
    expect(mapToCountryCode("us")).toBe("US");
    expect(mapToCountryCode("france")).toBe("FR");
    expect(mapToCountryCode("UNITED STATES")).toBe("US");
  });

  test("handles category arrays", () => {
    expect(mapToCountryCode(["US"])).toBe("US");
    expect(mapToCountryCode(["France", "Europe"])).toBe("FR");
    expect(mapToCountryCode(["AU"])).toBe("AU");
  });

  test("handles common variations", () => {
    expect(mapToCountryCode("USA")).toBe("US");
    expect(mapToCountryCode("UK")).toBe("GB");
    expect(mapToCountryCode("South Korea")).toBe("KR");
    expect(mapToCountryCode("Czech Republic")).toBe("CZ");
    expect(mapToCountryCode("North Korea")).toBe("KP");
    expect(mapToCountryCode("Russia")).toBe("RU");
    expect(mapToCountryCode("South Africa")).toBe("ZA");
  });

  test("returns null for invalid input", () => {
    expect(mapToCountryCode("InvalidCountry")).toBeNull();
    expect(mapToCountryCode("XX")).toBeNull();
    expect(mapToCountryCode("")).toBeNull();
  });

  test("returns null for array with no valid country codes", () => {
    expect(mapToCountryCode(["Invalid", "AlsoInvalid"])).toBeNull();
    expect(mapToCountryCode(["XX", "YY"])).toBeNull();
    expect(mapToCountryCode([])).toBeNull();
  });

  test("handles array with mixed valid and invalid entries", () => {
    expect(mapToCountryCode(["Invalid", "US", "AlsoInvalid"])).toBe("US");
    expect(mapToCountryCode(["XX", "FR"])).toBe("FR");
  });

  test("handles whitespace in input", () => {
    expect(mapToCountryCode("  US  ")).toBe("US");
    expect(mapToCountryCode("  United States  ")).toBe("US");
  });

  test("handles invalid 2-letter codes", () => {
    expect(mapToCountryCode("XX")).toBeNull();
    expect(mapToCountryCode("ZZ")).toBeNull();
  });
});

describe("extractSafetyCategories", () => {
  test("extracts crime category", () => {
    const summary = "Crime is a concern. Theft and robbery are common.";
    const categories = extractSafetyCategories(summary);
    expect(categories.some((category) => category.category === "crime")).toBe(true);
  });

  test("extracts terrorism category", () => {
    const summary = "Terrorist attacks may occur with little warning.";
    const categories = extractSafetyCategories(summary);
    expect(categories.some((category) => category.category === "terrorism")).toBe(true);
  });

  test("extracts health category", () => {
    const summary = "Health risks include disease outbreaks.";
    const categories = extractSafetyCategories(summary);
    expect(categories.some((category) => category.category === "health")).toBe(true);
  });

  test("extracts civil unrest category", () => {
    const summary = "Demonstrations and protests occur regularly.";
    const categories = extractSafetyCategories(summary);
    expect(categories.some((category) => category.category === "civil unrest")).toBe(
      true
    );
  });

  test("extracts multiple categories", () => {
    const summary = "Crime and terrorism are concerns. Health risks also exist.";
    const categories = extractSafetyCategories(summary);
    expect(categories.length).toBeGreaterThan(1);
    expect(categories.some((category) => category.category === "crime")).toBe(true);
    expect(categories.some((category) => category.category === "terrorism")).toBe(true);
    expect(categories.some((category) => category.category === "health")).toBe(true);
  });

  test("returns empty array for summary without risk keywords", () => {
    const summary = "This is a safe destination with no concerns.";
    const categories = extractSafetyCategories(summary);
    expect(categories).toEqual([]);
  });

  test("includes description from relevant sentence", () => {
    const summary =
      "Overall safe. Crime is a concern in urban areas. Terrorism risk exists.";
    const categories = extractSafetyCategories(summary);
    const crimeCategory = categories.find((category) => category.category === "crime");
    expect(crimeCategory?.description).toBeTruthy();
    expect(crimeCategory?.description).toContain("Crime");
  });
});
