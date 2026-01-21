/** @vitest-environment node */

import type { PlacesPhotoRequest } from "@schemas/api";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GooglePlacesPhotoError } from "@/lib/google/errors";
import { handlePlacesPhoto } from "../_handler";

const MOCK_GET_PLACE_PHOTO = vi.hoisted(() => vi.fn());

vi.mock("@/lib/google/client", () => ({
  getPlacePhoto: MOCK_GET_PLACE_PHOTO,
}));

/**
 * Creates a mock Response object with a streaming body.
 *
 * @param bytes - The body content as a byte array.
 * @param headers - Optional HTTP headers for the response.
 * @returns A Response object containing the streamed bytes.
 */
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

  it("returns 413 when buffering exceeds limit", async () => {
    // MAX_PLACES_PHOTO_BYTES is 10 * 1024 * 1024
    const largeBuffer = new Uint8Array(10 * 1024 * 1024 + 1);
    MOCK_GET_PLACE_PHOTO.mockResolvedValue(
      createStreamResponse(largeBuffer, {
        "content-type": "image/jpeg",
      })
    );

    const res = await handlePlacesPhoto({ apiKey: "test" }, params);
    expect(res.status).toBe(413);
    const body = await res.json();
    expect(body.error).toBe("payload_too_large");
    expect(body.reason).toContain("exceeds size limit");
  });

  it("handles GooglePlacesPhotoError", async () => {
    const error = new GooglePlacesPhotoError(
      "Limit exceeded",
      "redirect_limit_exceeded",
      400
    );
    MOCK_GET_PLACE_PHOTO.mockRejectedValue(error);

    const res = await handlePlacesPhoto({ apiKey: "test" }, params);
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("redirect_limit_exceeded");
    expect(body.reason).toBe("Limit exceeded");
  });

  it("handles upstream non-ok response", async () => {
    MOCK_GET_PLACE_PHOTO.mockResolvedValue({
      headers: new Headers(),
      ok: false,
      status: 404,
    } as Response);

    const res = await handlePlacesPhoto({ apiKey: "test" }, params);
    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.error).toBe("external_api_error");
    expect(body.reason).toContain("Places API returned 404");
  });
});
