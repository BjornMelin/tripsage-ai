/** @vitest-environment node */

import type { toolRegistry } from "@ai/tools";
import type { ToolCallOptions } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

// Mock server-only module before imports
vi.mock("server-only", () => ({}));

// Mock telemetry
const mockSpan = {
  addEvent: vi.fn(),
  end: vi.fn(),
  setAttribute: vi.fn(),
};

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    (
      _name: string,
      _opts: unknown,
      fn: (span: typeof mockSpan) => Promise<unknown>
    ) => {
      return fn(mockSpan);
    }
  ),
}));

import {
  getRegistryTool,
  invokeTool,
  type RegisteredTool,
  requireTool,
} from "../registry-utils";

describe("requireTool", () => {
  it("should return tool when valid with execute function", () => {
    const mockTool = {
      description: "Test tool",
      execute: vi.fn(),
      inputSchema: z.object({ query: z.string() }),
    };

    const result = requireTool<{ query: string }, { data: string }>(
      mockTool,
      "testTool"
    );

    expect(result).toBe(mockTool);
    expect(result.execute).toBeDefined();
  });

  it("should throw error when tool is undefined", () => {
    expect(() => requireTool(undefined, "missingTool")).toThrow(
      "Tool missingTool not registered in toolRegistry"
    );
  });

  it("should throw error when tool is null", () => {
    expect(() => requireTool(null, "nullTool")).toThrow(
      "Tool nullTool not registered in toolRegistry"
    );
  });

  it("should throw error when tool lacks execute function", () => {
    const toolWithoutExecute = {
      description: "Tool without execute",
      inputSchema: z.object({}),
    };

    expect(() => requireTool(toolWithoutExecute, "noExecuteTool")).toThrow(
      "Tool noExecuteTool missing execute binding"
    );
  });

  it("should throw error when execute is not a function", () => {
    const toolWithNonFunctionExecute = {
      description: "Tool with non-function execute",
      execute: "not a function",
      inputSchema: z.object({}),
    };

    expect(() => requireTool(toolWithNonFunctionExecute, "badExecuteTool")).toThrow(
      "Tool badExecuteTool missing execute binding"
    );
  });
});

describe("getRegistryTool", () => {
  it("should retrieve and validate tool from registry", () => {
    const mockRegistry = {
      webSearch: {
        description: "Web search tool",
        execute: vi.fn(),
        inputSchema: z.object({ query: z.string() }),
      },
    } as unknown as typeof toolRegistry;

    const result = getRegistryTool<{ query: string }, { results: string[] }>(
      mockRegistry,
      "webSearch" as keyof typeof mockRegistry
    );

    expect(result).toBe(mockRegistry.webSearch);
    expect(result.description).toBe("Web search tool");
  });

  it("should throw for missing registry tool", () => {
    const mockRegistry = {} as unknown as typeof toolRegistry;

    expect(() =>
      getRegistryTool(mockRegistry, "nonexistent" as keyof typeof mockRegistry)
    ).toThrow("Tool nonexistent not registered in toolRegistry");
  });
});

describe("invokeTool", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should execute tool and return result", async () => {
    const expectedResult = { data: "test result" };
    const mockTool: RegisteredTool<{ query: string }, { data: string }> = {
      description: "Test tool",
      execute: vi.fn().mockResolvedValue(expectedResult),
      inputSchema: z.object({ query: z.string() }),
    };

    const params = { query: "test query" };
    const callOptions: ToolCallOptions = {
      messages: [],
      toolCallId: "test-call-1",
    };

    const result = await invokeTool(mockTool, params, callOptions);

    expect(result).toEqual(expectedResult);
    expect(mockTool.execute).toHaveBeenCalledWith(params, callOptions);
  });

  it("should handle synchronous execute functions", async () => {
    const expectedResult = { data: "sync result" };
    const mockTool: RegisteredTool<{ id: string }, { data: string }> = {
      description: "Sync tool",
      execute: vi.fn().mockReturnValue(expectedResult),
      inputSchema: z.object({ id: z.string() }),
    };

    const params = { id: "123" };
    const result = await invokeTool(mockTool, params);

    expect(result).toEqual(expectedResult);
    expect(mockTool.execute).toHaveBeenCalledWith(params, undefined);
  });

  it("should propagate errors from tool execution", async () => {
    const mockTool: RegisteredTool<{ query: string }, { error: string }> = {
      description: "Failing tool",
      execute: vi.fn().mockRejectedValue(new Error("Tool execution failed")),
      inputSchema: z.object({ query: z.string() }),
    };

    const params = { query: "fail" };

    await expect(invokeTool(mockTool, params)).rejects.toThrow("Tool execution failed");
  });

  it("should work without callOptions", async () => {
    const expectedResult = { success: true };
    const mockTool: RegisteredTool<{ action: string }, { success: boolean }> = {
      description: "Optional options tool",
      execute: vi.fn().mockResolvedValue(expectedResult),
      inputSchema: z.object({ action: z.string() }),
    };

    const params = { action: "test" };
    const result = await invokeTool(mockTool, params);

    expect(result).toEqual(expectedResult);
    expect(mockTool.execute).toHaveBeenCalledWith(params, undefined);
  });

  it("should include tool metadata in telemetry span", async () => {
    const { withTelemetrySpan } = await import("@/lib/telemetry/span");

    const mockTool = {
      description: "Telemetry test tool",
      execute: vi.fn().mockResolvedValue({ data: "result" }),
      inputSchema: z.object({ query: z.string() }),
      name: "telemetryTool",
    } as unknown as RegisteredTool<{ query: string }, { data: string }>;

    await invokeTool(mockTool, { query: "test" });

    expect(withTelemetrySpan).toHaveBeenCalledWith(
      "agent.tool.execute",
      expect.objectContaining({
        attributes: expect.objectContaining({
          hasCallOptions: false,
          toolDescription: "Telemetry test tool",
          toolName: "telemetryTool",
        }),
      }),
      expect.any(Function)
    );
  });
});
