/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installUpstashMocks, resetUpstashMocks } from "@/test/upstash";

const mockSpan = vi.hoisted(() => ({
  end: vi.fn(),
  recordException: vi.fn(),
  setAttribute: vi.fn(),
  setStatus: vi.fn(),
}));

const GET_ENV_FALLBACK = vi.hoisted(() => vi.fn());
const GET_REQUIRED_SERVER_ORIGIN = vi.hoisted(() => vi.fn(() => "https://example.com"));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: (...args: unknown[]) => GET_ENV_FALLBACK(...args),
}));

vi.mock("@/lib/url/server-origin", () => ({
  getRequiredServerOrigin: () => GET_REQUIRED_SERVER_ORIGIN(),
}));

vi.mock("@/lib/telemetry/span", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/telemetry/span")>();
  return {
    ...actual,
    recordTelemetryEvent: vi.fn(),
    withTelemetrySpan: vi.fn((_name: string, _opts: unknown, execute: unknown) =>
      (execute as (span: unknown) => unknown)(mockSpan)
    ),
  };
});

describe("enqueueJob", () => {
  const { qstash } = installUpstashMocks();

  beforeEach(() => {
    resetUpstashMocks();
    GET_REQUIRED_SERVER_ORIGIN.mockReturnValue("https://example.com");
  });

  afterEach(async () => {
    const { setQStashClientFactoryForTests } = await import("@/lib/qstash/client");
    setQStashClientFactoryForTests(null);
    GET_ENV_FALLBACK.mockReset();
    GET_REQUIRED_SERVER_ORIGIN.mockReset();
    mockSpan.setAttribute.mockReset();
  });

  it("passes label, flowControl, and failureCallback to publishJSON", async () => {
    const { enqueueJob, setQStashClientFactoryForTests } = await import(
      "@/lib/qstash/client"
    );
    setQStashClientFactoryForTests(() => new qstash.Client({ token: "test" }));

    const result = await enqueueJob("test-job", { ok: true }, "/api/jobs/test", {
      failureCallback: "https://example.com/failure",
      flowControl: { key: "tenant-1", parallelism: 2 },
      label: "tripsage:test",
      timeout: 30,
    });

    const messages = qstash.__getMessages();
    expect(messages).toHaveLength(1);
    expect(messages[0]?.url).toBe("https://example.com/api/jobs/test");
    expect(messages[0]?.label).toBe("tripsage:test");
    expect(messages[0]?.flowControl).toEqual({ key: "tenant-1", parallelism: 2 });
    expect(messages[0]?.failureCallback).toBe("https://example.com/failure");
    expect(messages[0]?.timeout).toBe(30);
    expect(result?.messageId).toBe("qstash-mock-1");
  });

  it("records telemetry attributes for label, flow control, and failure callback", async () => {
    const { enqueueJob, setQStashClientFactoryForTests } = await import(
      "@/lib/qstash/client"
    );
    setQStashClientFactoryForTests(() => new qstash.Client({ token: "test" }));

    await enqueueJob("test-job", { ok: true }, "/api/jobs/test", {
      failureCallback: "https://example.com/failure",
      flowControl: { key: "tenant-42", rate: 5 },
      label: "tripsage:test",
    });

    expect(mockSpan.setAttribute).toHaveBeenCalledWith("qstash.label", "tripsage:test");
    expect(mockSpan.setAttribute).toHaveBeenCalledWith(
      "qstash.flow_control_key",
      "tenant-42"
    );
    expect(mockSpan.setAttribute).toHaveBeenCalledWith(
      "qstash.has_failure_callback",
      true
    );
  });

  it("throws when the server-origin contract cannot resolve a callback origin", async () => {
    GET_REQUIRED_SERVER_ORIGIN.mockImplementation(() => {
      throw new Error("Server origin not configured");
    });

    const { enqueueJob, setQStashClientFactoryForTests } = await import(
      "@/lib/qstash/client"
    );
    setQStashClientFactoryForTests(() => new qstash.Client({ token: "test" }));

    await expect(
      enqueueJob("test-job", { ok: true }, "/api/jobs/test")
    ).rejects.toThrow("Server origin not configured");

    expect(mockSpan.setAttribute).toHaveBeenCalledWith("qstash.missing_origin", true);
  });

  it.each([
    "https://evil.example/api/jobs/test",
    "//evil.example/api/jobs/test",
  ])("rejects off-origin job path %s", async (path) => {
    const { enqueueJob, setQStashClientFactoryForTests } = await import(
      "@/lib/qstash/client"
    );
    setQStashClientFactoryForTests(() => new qstash.Client({ token: "test" }));

    await expect(enqueueJob("test-job", { ok: true }, path)).rejects.toThrow(
      "QStash job path must be a same-origin absolute path"
    );

    expect(qstash.__getMessages()).toHaveLength(0);
    expect(mockSpan.setAttribute).toHaveBeenCalledWith("qstash.invalid_path", true);
  });
});
