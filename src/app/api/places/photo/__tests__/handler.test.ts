/** @vitest-environment node */

import type { PlacesPhotoRequest } from "@schemas/api";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { handlePlacesPhoto } from "../_handler";

const MOCK_GET_PLACE_PHOTO = vi.hoisted(() => vi.fn());

vi.mock("@/lib/google/client", () => ({
  getPlacePhoto: MOCK_GET_PLACE_PHOTO,
}));

function createStreamResponse(
  bytes: Uint8Array,
  headers: Record<string, string> = {}
): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(bytes);
      controller.close();
    },
  });
  return new Response(stream, { headers, status: 200 });
}

describe("handlePlacesPhoto", () => {
  const params: PlacesPhotoRequest = {
    name: "places/test-photo",
  };

  beforeEach(() => {
    MOCK_GET_PLACE_PHOTO.mockReset();
  });

  it("returns 413 when content-length exceeds limit", async () => {
    MOCK_GET_PLACE_PHOTO.mockResolvedValue(
      createStreamResponse(new Uint8Array([1]), {
        "content-length": String(11 * 1024 * 1024),
        "content-type": "image/jpeg",
      })
    );

    const res = await handlePlacesPhoto({ apiKey: "test" }, params);
    expect(res.status).toBe(413);
  });

  it("streams when content-length is present and within limit", async () => {
    MOCK_GET_PLACE_PHOTO.mockResolvedValue(
      createStreamResponse(new Uint8Array([1, 2, 3]), {
        "content-length": "3",
        "content-type": "image/jpeg",
      })
    );

    const res = await handlePlacesPhoto({ apiKey: "test" }, params);
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toBe("image/jpeg");
    expect(res.headers.get("content-length")).toBe("3");
  });

  it("buffers with limit when content-length is missing", async () => {
    MOCK_GET_PLACE_PHOTO.mockResolvedValue(
      createStreamResponse(new Uint8Array([4, 5]), {
        "content-type": "image/jpeg",
      })
    );

    const res = await handlePlacesPhoto({ apiKey: "test" }, params);
    expect(res.status).toBe(200);
    const data = new Uint8Array(await res.arrayBuffer());
    expect(Array.from(data)).toEqual([4, 5]);
  });
});
