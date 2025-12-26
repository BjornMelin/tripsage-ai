/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { decodePolyline, encodePolyline } from "../polyline";

describe("google polyline utils", () => {
  it("decodes a known polyline sample", () => {
    const encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@";
    const coordinates = decodePolyline(encoded);

    expect(coordinates).toHaveLength(3);
    expect(coordinates[0][0]).toBeCloseTo(38.5, 5);
    expect(coordinates[0][1]).toBeCloseTo(-120.2, 5);
    expect(coordinates[1][0]).toBeCloseTo(40.7, 5);
    expect(coordinates[1][1]).toBeCloseTo(-120.95, 5);
    expect(coordinates[2][0]).toBeCloseTo(43.252, 5);
    expect(coordinates[2][1]).toBeCloseTo(-126.453, 5);
  });

  it("round-trips coordinates through encode/decode", () => {
    const coordinates: Array<[number, number]> = [
      [38.5, -120.2],
      [40.7, -120.95],
      [43.252, -126.453],
    ];

    const encoded = encodePolyline(coordinates);
    expect(encoded).toBe("_p~iF~ps|U_ulLnnqC_mqNvxq`@");
    expect(decodePolyline(encoded)).toEqual(coordinates);
  });
});
