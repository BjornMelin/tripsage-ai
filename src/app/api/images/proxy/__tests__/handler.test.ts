/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import { server } from "@/test/msw/server";

let handleRemoteImageProxy: typeof import("../_handler").handleRemoteImageProxy;

describe("handleRemoteImageProxy", () => {
  beforeEach(async () => {
    vi.unstubAllEnvs();
    __resetServerEnvCacheForTest();
    vi.resetModules();
    ({ handleRemoteImageProxy } = await import("../_handler"));
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    __resetServerEnvCacheForTest();
  });

  it("returns 403 when the remote host is not allowlisted", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "example.com");
    __resetServerEnvCacheForTest();

    const response = await handleRemoteImageProxy({
      url: "https://not-example.com/image.png",
    });

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: "forbidden" })
    );
  });

  it("rejects IP-literal targets even when explicitly allowlisted", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "127.0.0.1,example.com");
    __resetServerEnvCacheForTest();

    const response = await handleRemoteImageProxy({
      url: "https://127.0.0.1/image.png",
    });

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: "forbidden" })
    );
  });

  it("proxies a valid remote image response", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "example.com");
    __resetServerEnvCacheForTest();

    const bytes = new Uint8Array([0x00, 0x01, 0x02]);
    server.use(
      http.get("https://example.com/image.png", () => {
        return HttpResponse.arrayBuffer(bytes.buffer, {
          headers: {
            "content-length": String(bytes.byteLength),
            "content-type": "image/png",
          },
          status: 200,
        });
      })
    );

    const response = await handleRemoteImageProxy({
      url: "https://example.com/image.png",
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("public, max-age=86400");
    expect(response.headers.get("content-type")).toBe("image/png");

    const buffered = new Uint8Array(await response.arrayBuffer());
    expect(Array.from(buffered)).toEqual(Array.from(bytes));
  });

  it("returns 415 when the upstream response is not an image", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "example.com");
    __resetServerEnvCacheForTest();

    server.use(
      http.get("https://example.com/image.png", () => {
        return new HttpResponse("nope", {
          headers: {
            "content-type": "text/plain",
          },
          status: 200,
        });
      })
    );

    const response = await handleRemoteImageProxy({
      url: "https://example.com/image.png",
    });

    expect(response.status).toBe(415);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: "unsupported_media_type" })
    );
  });

  it("returns 413 when the upstream content-length exceeds the configured limit", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "example.com");
    vi.stubEnv("IMAGE_PROXY_MAX_BYTES", "1");
    __resetServerEnvCacheForTest();

    server.use(
      http.get("https://example.com/image.png", () => {
        return HttpResponse.arrayBuffer(new Uint8Array([0x00, 0x01]).buffer, {
          headers: {
            "content-length": "2",
            "content-type": "image/png",
          },
          status: 200,
        });
      })
    );

    const response = await handleRemoteImageProxy({
      url: "https://example.com/image.png",
    });

    expect(response.status).toBe(413);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: "payload_too_large" })
    );
  });

  it("returns 413 when streaming body exceeds the limit without content-length", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "example.com");
    vi.stubEnv("IMAGE_PROXY_MAX_BYTES", "1");
    __resetServerEnvCacheForTest();

    server.use(
      http.get("https://example.com/image.png", () => {
        return HttpResponse.arrayBuffer(new Uint8Array([0x00, 0x01]).buffer, {
          headers: {
            "content-type": "image/png",
          },
          status: 200,
        });
      })
    );

    const response = await handleRemoteImageProxy({
      url: "https://example.com/image.png",
    });

    expect(response.status).toBe(413);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: "payload_too_large" })
    );
  });

  it("rejects when redirect escapes the allowlist", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "example.com");
    __resetServerEnvCacheForTest();

    server.use(
      http.get("https://example.com/redirect-to-evil", () => {
        return HttpResponse.redirect("https://evil.com/image.png");
      }),
      http.get("https://evil.com/image.png", () => {
        return HttpResponse.arrayBuffer(new Uint8Array([0x00]).buffer, {
          headers: {
            "content-type": "image/png",
          },
          status: 200,
        });
      })
    );

    const response = await handleRemoteImageProxy({
      url: "https://example.com/redirect-to-evil",
    });

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: "forbidden" })
    );
  });
});
