/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { handlePlacesPhoto } from "../_handler";

const placePhotoMediaUrlPattern =
  /^https:\/\/places\.googleapis\.com\/v1\/places\/[^/]+\/photos\/[^/]+\/media/;

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

  it("returns 502 when redirect host is not allowed", async () => {
    server.use(
      http.get(placePhotoMediaUrlPattern, () => {
        return new HttpResponse(null, {
          headers: { location: "https://evil.example.com/photo" },
          status: 302,
        });
      })
    );

    const response = await handlePlacesPhoto(
      { apiKey: "test-key" },
      { maxWidthPx: 400, name: "places/ABC123/photos/XYZ789" }
    );

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      error: "redirect_host_not_allowed",
    });
  });

  it("returns 502 when redirect limit is exceeded", async () => {
    const redirectUrls = [
      "https://googleusercontent.com/photo/0",
      "https://googleusercontent.com/photo/1",
      "https://googleusercontent.com/photo/2",
      "https://googleusercontent.com/photo/3",
    ];

    server.use(
      http.get(placePhotoMediaUrlPattern, () => {
        return new HttpResponse(null, {
          headers: { location: redirectUrls[0] },
          status: 302,
        });
      }),
      http.get(redirectUrls[0], () => {
        return new HttpResponse(null, {
          headers: { location: redirectUrls[1] },
          status: 302,
        });
      }),
      http.get(redirectUrls[1], () => {
        return new HttpResponse(null, {
          headers: { location: redirectUrls[2] },
          status: 302,
        });
      }),
      http.get(redirectUrls[2], () => {
        return new HttpResponse(null, {
          headers: { location: redirectUrls[3] },
          status: 302,
        });
      })
    );

    const response = await handlePlacesPhoto(
      { apiKey: "test-key" },
      { maxWidthPx: 400, name: "places/ABC123/photos/XYZ789" }
    );

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      error: "redirect_limit_exceeded",
    });
  });

  it("returns upstream status for 4xx responses", async () => {
    server.use(
      http.get(placePhotoMediaUrlPattern, () => {
        return HttpResponse.json({ error: "quota" }, { status: 403 });
      })
    );

    const response = await handlePlacesPhoto(
      { apiKey: "test-key" },
      { maxWidthPx: 400, name: "places/ABC123/photos/XYZ789" }
    );

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toMatchObject({
      error: "external_api_error",
    });
  });

  it("returns 502 for upstream 5xx responses", async () => {
    server.use(
      http.get(placePhotoMediaUrlPattern, () => {
        return HttpResponse.json({ error: "upstream_failed" }, { status: 500 });
      })
    );

    const response = await handlePlacesPhoto(
      { apiKey: "test-key" },
      { maxWidthPx: 400, name: "places/ABC123/photos/XYZ789" }
    );

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      error: "external_api_error",
    });
  });

  it("returns photo response with cache headers on success", async () => {
    const photoBytes = new Uint8Array([1, 2, 3, 4]);

    server.use(
      http.get(placePhotoMediaUrlPattern, () => {
        return new HttpResponse(null, {
          headers: { location: "https://googleusercontent.com/photo/success" },
          status: 302,
        });
      }),
      http.get("https://googleusercontent.com/photo/success", () => {
        return new HttpResponse(photoBytes, {
          headers: { "Content-Type": "image/png" },
          status: 200,
        });
      })
    );

    const response = await handlePlacesPhoto(
      { apiKey: "test-key" },
      { maxWidthPx: 400, name: "places/ABC123/photos/XYZ789" }
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("public, max-age=86400");
    expect(response.headers.get("content-type")).toBe("image/png");
    const buffer = await response.arrayBuffer();
    expect(buffer.byteLength).toBe(photoBytes.byteLength);
  });
});
