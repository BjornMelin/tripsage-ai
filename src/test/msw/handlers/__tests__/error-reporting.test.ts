/** @vitest-environment node */

import type { ErrorReport } from "@schemas/errors";
import { describe, expect, it } from "vitest";
import {
  createFlakyErrorReportingHandler,
  ERROR_REPORTING_ENDPOINT,
} from "@/test/msw/handlers/error-reporting";
import { server } from "@/test/msw/server";

const buildReport = (): ErrorReport => ({
  error: {
    message: "Test error",
    name: "Error",
  },
  timestamp: new Date().toISOString(),
  url: "https://example.com/",
  userAgent: "Vitest",
});

describe("error reporting MSW handlers", () => {
  it("simulates rejected fetches before returning a successful response", async () => {
    const flaky = createFlakyErrorReportingHandler({
      endpoint: ERROR_REPORTING_ENDPOINT,
      failTimes: 1,
    });
    server.use(flaky.handler);

    await expect(
      fetch(ERROR_REPORTING_ENDPOINT, {
        body: JSON.stringify(buildReport()),
        method: "POST",
      })
    ).rejects.toThrow();

    const response = await fetch(ERROR_REPORTING_ENDPOINT, {
      body: JSON.stringify(buildReport()),
      method: "POST",
    });

    expect(response.ok).toBe(true);
    await expect(response.json()).resolves.toEqual({ success: true });
    expect(flaky.callCount()).toBe(2);
  });
});
