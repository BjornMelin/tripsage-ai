import type { Page, Route } from "@playwright/test";

type JsonFulfillOptions = {
  delayMs?: number;
  headers?: Record<string, string>;
  method?: string;
  status?: number;
};

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

export async function fulfillTextStream(route: Route, text: string): Promise<void> {
  await route.fulfill({
    body: buildTextDeltaStream(text),
    contentType: "text/event-stream",
    headers: { "x-vercel-ai-ui-message-stream": "v1" },
    status: 200,
  });
}

export async function mockTextStreamRoute<T>(
  page: Page,
  url: string,
  text: string,
  onBody?: (body: T) => void
): Promise<() => boolean> {
  let handled = false;

  await page.route(url, async (route) => {
    handled = true;
    try {
      onBody?.(route.request().postDataJSON() as T);
    } catch {
      onBody?.({} as T);
    }
    await fulfillTextStream(route, text);
  });

  return () => handled;
}
