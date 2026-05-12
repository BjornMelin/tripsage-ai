import type { Route } from "@playwright/test";

type JsonFulfillOptions = {
  headers?: Record<string, string>;
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
