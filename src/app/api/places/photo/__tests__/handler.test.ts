/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { handlePlacesPhoto } from "../_handler";

describe("handlePlacesPhoto", () => {
  it("returns 400 when required dimensions are missing", async () => {
    const response = await handlePlacesPhoto(
      { apiKey: "test-key" },
      { name: "places/ABC123/photos/XYZ789" }
    );

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toMatchObject({
      error: "missing_photo_dimensions",
    });
  });

  it("returns 400 when photo name is invalid", async () => {
    const response = await handlePlacesPhoto(
      { apiKey: "test-key" },
      { maxWidthPx: 400, name: "invalid-photo-name" }
    );

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toMatchObject({
      error: "invalid_photo_name",
    });
  });
});
