/** @vitest-environment node */

import { afterEach, describe, expect, it } from "vitest";
import {
  getPublishedQStashMessages,
  installUpstashMocks,
  teardownUpstashMocks,
} from "@/test/upstash";

describe("getPublishedQStashMessages", () => {
  afterEach(() => {
    teardownUpstashMocks();
  });

  it("throws when mocks are not installed", () => {
    teardownUpstashMocks();
    expect(() => getPublishedQStashMessages()).toThrowError(
      /Upstash mocks not installed; call installUpstashMocks\(\) in test setup/
    );
  });

  it("returns published messages after install", async () => {
    const { qstash } = installUpstashMocks();
    const client = new qstash.Client({ token: "test-token" });

    await client.publishJSON({
      body: { hello: "world" },
      url: "https://example.com/webhook",
    });

    const messages = getPublishedQStashMessages();
    expect(messages).toHaveLength(1);
    expect(messages[0].url).toBe("https://example.com/webhook");
  });
});
