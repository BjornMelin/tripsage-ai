import type { Page, Route } from "@playwright/test";

type JsonFulfillOptions = {
  delayMs?: number;
  headers?: Record<string, string>;
  method?: string;
  status?: number;
};

/**
 * Fulfill a Playwright route with a JSON response and stable defaults.
 *
 * @param route - Playwright route to fulfill.
 * @param body - JSON-serializable response body.
 * @param options - Optional response status, headers, delay, and method metadata.
 * @returns Promise that resolves after the route is fulfilled.
 * @see https://playwright.dev/docs/api/class-route#route-fulfill
 */
export async function fulfillJson(
  route: Route,
  body: unknown,
  options: JsonFulfillOptions = {}
): Promise<void> {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: "application/json",
    headers: options.headers,
    status: options.status ?? 200,
  });
}

/**
 * Register a JSON route mock, optionally scoped to one HTTP method.
 *
 * @param page - Playwright page that owns the route handler.
 * @param url - URL pattern accepted by `page.route`.
 * @param body - JSON-serializable response body.
 * @param options - Optional response status, headers, delay, and method filter.
 * @returns Promise that resolves after the route is registered.
 * @see https://playwright.dev/docs/network#handle-requests
 */
export async function mockJsonRoute(
  page: Page,
  url: string,
  body: unknown,
  options?: JsonFulfillOptions
): Promise<void> {
  await page.route(url, async (route) => {
    if (options?.method && route.request().method() !== options.method) {
      await route.continue();
      return;
    }

    if (options?.delayMs) {
      await new Promise((resolve) => setTimeout(resolve, options.delayMs));
    }
    await fulfillJson(route, body, options);
  });
}

function streamEvent(payload: unknown): string {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

/**
 * Build an AI SDK UI-message text stream fixture for chat E2E tests.
 *
 * @param text - Assistant text delta to emit in the stream.
 * @returns Serialized server-sent event stream payload.
 * @see https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
 */
export function buildTextDeltaStream(text: string): string {
  return [
    streamEvent({ messageId: "assistant-1", type: "start" }),
    streamEvent({ id: "text-1", type: "text-start" }),
    streamEvent({ delta: text, id: "text-1", type: "text-delta" }),
    streamEvent({ id: "text-1", type: "text-end" }),
    streamEvent({ finishReason: "stop", type: "finish" }),
    "data: [DONE]\n\n",
  ].join("");
}

/**
 * Fulfill a Playwright route with an AI SDK UI-message text stream.
 *
 * @param route - Playwright route to fulfill.
 * @param text - Assistant text delta to emit in the stream.
 * @returns Promise that resolves after the route is fulfilled.
 * @see https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
 */
export async function fulfillTextStream(route: Route, text: string): Promise<void> {
  await route.fulfill({
    body: buildTextDeltaStream(text),
    contentType: "text/event-stream",
    headers: { "x-vercel-ai-ui-message-stream": "v1" },
    status: 200,
  });
}

function readPostDataJson<T>(route: Route): T {
  try {
    return route.request().postDataJSON() as T;
  } catch {
    return {} as T;
  }
}

/**
 * Register a text stream route mock and expose whether it was called.
 *
 * @typeParam T - Expected JSON request body shape.
 * @param page - Playwright page that owns the route handler.
 * @param url - URL pattern accepted by `page.route`.
 * @param text - Assistant text delta to emit in the stream.
 * @param onBody - Optional assertion callback for the parsed request body.
 * @returns Function that reports whether the route handled at least one request.
 * @see https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
 */
export async function mockTextStreamRoute<T>(
  page: Page,
  url: string,
  text: string,
  onBody?: (body: T) => void
): Promise<() => boolean> {
  let handled = false;

  await page.route(url, async (route) => {
    handled = true;
    onBody?.(readPostDataJson<T>(route));
    await fulfillTextStream(route, text);
  });

  return () => handled;
}
