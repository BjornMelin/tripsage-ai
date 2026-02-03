import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

/**
 * MSW handlers for mocking remote image proxy endpoints in tests.
 */
export const imageProxyHandlers: HttpHandler[] = [
  http.get("https://example.com/image.png", () => {
    return HttpResponse.arrayBuffer(new Uint8Array([0x00]).buffer, {
      headers: {
        "content-type": "image/png",
      },
      status: 200,
    });
  }),
];
