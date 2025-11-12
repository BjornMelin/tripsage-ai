import { describe, expect, it } from "vitest";
import { parseSchemaCard } from "../parse-schema-card";

describe("parseSchemaCard", () => {
  it("should parse codefenced JSON with flight schema", () => {
    const text = `\`\`\`json
{
  "schemaVersion": "flight.v1",
  "offers": []
}
\`\`\``;
    const result = parseSchemaCard(text);
    expect(result).not.toBeNull();
    expect(result?.kind).toBe("flight");
  });

  it("should parse plain JSON with stay schema", () => {
    const text = `{
      "schemaVersion": "stay.v1",
      "listings": []
    }`;
    const result = parseSchemaCard(text);
    expect(result).not.toBeNull();
    expect(result?.kind).toBe("stay");
  });

  it("should parse codefenced JSON without language tag", () => {
    const text = `\`\`\`
{
  "schemaVersion": "budget.v1",
  "breakdown": {}
}
\`\`\``;
    const result = parseSchemaCard(text);
    expect(result).not.toBeNull();
    expect(result?.kind).toBe("budget");
  });

  it("should return null for invalid JSON", () => {
    const text = "not json at all";
    const result = parseSchemaCard(text);
    expect(result).toBeNull();
  });

  it("should return null for valid JSON without matching schema", () => {
    const text = `{
      "someOtherSchema": "v1",
      "data": "test"
    }`;
    const result = parseSchemaCard(text);
    expect(result).toBeNull();
  });

  it("should return null for empty string", () => {
    const result = parseSchemaCard("");
    expect(result).toBeNull();
  });

  it("should parse destination schema", () => {
    const text = `{
      "schemaVersion": "dest.v1",
      "destination": "Tokyo"
    }`;
    const result = parseSchemaCard(text);
    expect(result).not.toBeNull();
    expect(result?.kind).toBe("destination");
  });

  it("should parse itinerary schema", () => {
    const text = `{
      "schemaVersion": "itin.v1",
      "days": []
    }`;
    const result = parseSchemaCard(text);
    expect(result).not.toBeNull();
    expect(result?.kind).toBe("itinerary");
  });

  it("should handle JSON with extra whitespace in codefence", () => {
    const text = `\`\`\`json
    {
      "schemaVersion": "flight.v1",
      "offers": []
    }
    \`\`\``;
    const result = parseSchemaCard(text);
    expect(result).not.toBeNull();
    expect(result?.kind).toBe("flight");
  });

  it("should handle non-object JSON", () => {
    const text = `"just a string"`;
    const result = parseSchemaCard(text);
    expect(result).toBeNull();
  });
});
