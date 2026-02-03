/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import { resetRemoteImageProxyAllowedHostsCacheForTest } from "@/lib/images/remote-image-proxy.server";

import { handleRemoteImageProxy } from "../_handler";

describe("handleRemoteImageProxy", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    __resetServerEnvCacheForTest();
    resetRemoteImageProxyAllowedHostsCacheForTest();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    __resetServerEnvCacheForTest();
    resetRemoteImageProxyAllowedHostsCacheForTest();
  });

  it("returns 403 when the remote host is not allowlisted", async () => {
    vi.stubEnv("IMAGE_PROXY_ALLOWED_HOSTS", "example.com");
    __resetServerEnvCacheForTest();
    resetRemoteImageProxyAllowedHostsCacheForTest();

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
    resetRemoteImageProxyAllowedHostsCacheForTest();

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
    resetRemoteImageProxyAllowedHostsCacheForTest();

    const bytes = new Uint8Array([0x00, 0x01, 0x02]);
    const upstream = new Response(bytes, {
      headers: {
        "content-length": String(bytes.byteLength),
        "content-type": "image/png",
      },
      status: 200,
    });
    Object.defineProperty(upstream, "url", {
      configurable: true,
      value: "https://example.com/image.png",
    });

    const fetchMock = vi.fn(async () => upstream);
    vi.stubGlobal("fetch", fetchMock);

    const response = await handleRemoteImageProxy({
      url: "https://example.com/image.png",
    });

    expect(fetchMock).toHaveBeenCalledWith("https://example.com/image.png", {
      redirect: "follow",
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
    resetRemoteImageProxyAllowedHostsCacheForTest();

    const upstream = new Response("nope", {
      headers: {
        "content-type": "text/plain",
      },
      status: 200,
    });
    Object.defineProperty(upstream, "url", {
      configurable: true,
      value: "https://example.com/image.png",
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => upstream)
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
    resetRemoteImageProxyAllowedHostsCacheForTest();

    const upstream = new Response(new Uint8Array([0x00, 0x01]), {
      headers: {
        "content-length": "2",
        "content-type": "image/png",
      },
      status: 200,
    });
    Object.defineProperty(upstream, "url", {
      configurable: true,
      value: "https://example.com/image.png",
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => upstream)
    );

    const response = await handleRemoteImageProxy({
      url: "https://example.com/image.png",
    });

    expect(response.status).toBe(413);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: "payload_too_large" })
    );
  });
});
