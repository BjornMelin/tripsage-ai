/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  openTelemetryOptions: undefined as { runtimeContext?: boolean } | undefined,
  registerOTel: vi.fn(),
  registerTelemetry: vi.fn(),
}));

vi.mock("@ai-sdk/otel", () => ({
  OpenTelemetry: class {
    constructor(options?: { runtimeContext?: boolean }) {
      mocks.openTelemetryOptions = options;
    }
  },
}));

vi.mock("@vercel/otel", () => ({
  registerOTel: mocks.registerOTel,
}));

vi.mock("ai", () => ({
  registerTelemetry: mocks.registerTelemetry,
}));

import { register } from "@/instrumentation";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/constants";

describe("server instrumentation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.openTelemetryOptions = undefined;
    vi.stubEnv("NEXT_RUNTIME", "edge");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("registers AI SDK telemetry with the application tracer", async () => {
    await register();

    expect(mocks.registerOTel).toHaveBeenCalledWith({
      serviceName: TELEMETRY_SERVICE_NAME,
    });
    expect(mocks.openTelemetryOptions).toEqual({ runtimeContext: true });
    expect(mocks.registerTelemetry).toHaveBeenCalledOnce();
  });
});
