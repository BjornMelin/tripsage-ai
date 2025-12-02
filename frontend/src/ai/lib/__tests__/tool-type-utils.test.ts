/** @vitest-environment node */

import { type ToolSet, type TypedToolCall, type TypedToolResult, tool } from "ai";
import { describe, expect, expectTypeOf, it } from "vitest";
import { ZodError, z } from "zod";

import {
  type InferToolInput,
  type InferToolOutput,
  isStaticToolCall,
} from "../tool-type-utils";

/**
 * Create proper AI SDK v6 tools using the tool() function with Zod schemas.
 */
const calculatorSchema = z.object({
  a: z.number().describe("First number"),
  b: z.number().describe("Second number"),
});

const searchSchema = z.object({
  query: z.string().describe("Search query"),
});

// Create tools using AI SDK v6 tool() function
// Note: We validate inputs manually in execute to test error handling,
// as AI SDK v6 validates inputs when parsing tool calls from the model,
// not when execute is called directly.
const calculatorTool = tool<{ a: number; b: number }, { result: number }>({
  description: "Calculate the sum of two numbers",
  // biome-ignore lint/suspicious/useAwait: AI SDK v6 tool execute signature requires async
  execute: async (params) => {
    // Validate input using schema to test error handling
    const validated = calculatorSchema.parse(params);
    return { result: validated.a + validated.b };
  },
  inputSchema: calculatorSchema,
});

const searchTool = tool<{ query: string }, { items: string[] }>({
  description: "Search for items",
  // biome-ignore lint/suspicious/useAwait: AI SDK v6 tool execute signature requires async
  execute: async (params) => {
    // Validate input using schema to test error handling
    const validated = searchSchema.parse(params);
    return { items: [validated.query] };
  },
  inputSchema: searchSchema,
});

const testTools = {
  calculator: calculatorTool,
  search: searchTool,
} satisfies ToolSet;

describe("isStaticToolCall", () => {
  it("should return true for tool calls without dynamic flag", () => {
    const staticCall = {
      input: { query: "test" },
      toolCallId: "call-1",
      toolName: "search",
    };

    // Type assertion needed for test - in real usage TypedToolCall comes from AI SDK
    expect(isStaticToolCall(staticCall as Parameters<typeof isStaticToolCall>[0])).toBe(
      true
    );
  });

  it("should return true for tool calls with dynamic=false", () => {
    const staticCall = {
      dynamic: false,
      input: { a: 1, b: 2 },
      toolCallId: "call-2",
      toolName: "calculator",
    };

    expect(isStaticToolCall(staticCall as Parameters<typeof isStaticToolCall>[0])).toBe(
      true
    );
  });

  it("should return false for tool calls with dynamic=true", () => {
    const dynamicCall = {
      dynamic: true,
      input: { query: "dynamic" },
      toolCallId: "call-3",
      toolName: "search",
    };

    expect(
      isStaticToolCall(dynamicCall as Parameters<typeof isStaticToolCall>[0])
    ).toBe(false);
  });

  it("should enable type narrowing for switch statements", () => {
    const toolCall = {
      input: { a: 5, b: 3 },
      toolCallId: "call-4",
      toolName: "calculator",
    };

    const typedCall = toolCall as Parameters<typeof isStaticToolCall>[0];

    if (isStaticToolCall(typedCall)) {
      // After type guard, we can safely switch on toolName
      switch (typedCall.toolName) {
        case "calculator":
          expect(typedCall.toolName).toBe("calculator");
          break;
        case "search":
          expect(typedCall.toolName).toBe("search");
          break;
        default:
          // TypeScript should catch unhandled cases
          break;
      }
    }

    expect(isStaticToolCall(typedCall)).toBe(true);
  });
});

describe("Tool type utilities integration", () => {
  it("should work with AI SDK v6 tool() function", () => {
    // Verify tools created with tool() have expected structure
    expect(calculatorTool).toHaveProperty("execute");
    expect(calculatorTool).toHaveProperty("inputSchema");
    expect(calculatorTool).toHaveProperty("description");

    expect(searchTool).toHaveProperty("execute");
    expect(searchTool).toHaveProperty("inputSchema");
    expect(searchTool).toHaveProperty("description");
  });

  it("should allow ToolSet to contain multiple tools", () => {
    expect(Object.keys(testTools)).toEqual(["calculator", "search"]);
    expect(testTools.calculator).toBeDefined();
    expect(testTools.search).toBeDefined();
  });

  it("should execute tools with correct input/output types", async () => {
    const calcExecute = testTools.calculator.execute;
    expect(calcExecute).toBeDefined();
    if (!calcExecute) return;

    const calcResult = await calcExecute(
      { a: 10, b: 5 },
      { messages: [], toolCallId: "test-1" }
    );
    expect(calcResult).toEqual({ result: 15 });

    const searchExecute = testTools.search.execute;
    expect(searchExecute).toBeDefined();
    if (!searchExecute) return;

    const searchResult = await searchExecute(
      { query: "hello" },
      { messages: [], toolCallId: "test-2" }
    );
    expect(searchResult).toEqual({ items: ["hello"] });
  });

  describe("error handling for invalid inputs", () => {
    describe("calculator tool", () => {
      it("should reject when missing required field 'b'", async () => {
        const calcExecute = testTools.calculator.execute;
        expect(calcExecute).toBeDefined();
        if (!calcExecute) return;

        await expect(
          calcExecute({ a: 1 } as unknown as { a: number; b: number }, {
            messages: [],
            toolCallId: "error-calc-missing-b",
          })
        ).rejects.toThrow(ZodError);
      });

      it("should reject when missing required field 'a'", async () => {
        const calcExecute = testTools.calculator.execute;
        expect(calcExecute).toBeDefined();
        if (!calcExecute) return;

        await expect(
          calcExecute({ b: 2 } as unknown as { a: number; b: number }, {
            messages: [],
            toolCallId: "error-calc-missing-a",
          })
        ).rejects.toThrow(ZodError);
      });

      it("should reject when 'a' has wrong type (string)", async () => {
        const calcExecute = testTools.calculator.execute;
        expect(calcExecute).toBeDefined();
        if (!calcExecute) return;

        await expect(
          calcExecute({ a: "x", b: 2 } as unknown as { a: number; b: number }, {
            messages: [],
            toolCallId: "error-calc-wrong-type-a",
          })
        ).rejects.toThrow(ZodError);
      });

      it("should reject when 'b' has wrong type (string)", async () => {
        const calcExecute = testTools.calculator.execute;
        expect(calcExecute).toBeDefined();
        if (!calcExecute) return;

        await expect(
          calcExecute({ a: 1, b: "y" } as unknown as { a: number; b: number }, {
            messages: [],
            toolCallId: "error-calc-wrong-type-b",
          })
        ).rejects.toThrow(ZodError);
      });
    });

    describe("search tool", () => {
      it("should reject when missing required field 'query'", async () => {
        const searchExecute = testTools.search.execute;
        expect(searchExecute).toBeDefined();
        if (!searchExecute) return;

        await expect(
          searchExecute({} as unknown as { query: string }, {
            messages: [],
            toolCallId: "error-search-missing-query",
          })
        ).rejects.toThrow(ZodError);
      });

      it("should reject when 'query' has wrong type (number)", async () => {
        const searchExecute = testTools.search.execute;
        expect(searchExecute).toBeDefined();
        if (!searchExecute) return;

        await expect(
          searchExecute({ query: 123 } as unknown as { query: string }, {
            messages: [],
            toolCallId: "error-search-wrong-type-query",
          })
        ).rejects.toThrow(ZodError);
      });

      it("should reject when 'query' is null", async () => {
        const searchExecute = testTools.search.execute;
        expect(searchExecute).toBeDefined();
        if (!searchExecute) return;

        await expect(
          searchExecute({ query: null } as unknown as { query: string }, {
            messages: [],
            toolCallId: "error-search-null-query",
          })
        ).rejects.toThrow(ZodError);
      });
    });
  });
});

describe("Type re-exports from AI SDK", () => {
  it("should infer tool input and output types", () => {
    type CalcInput = InferToolInput<typeof calculatorTool>;
    type CalcOutput = InferToolOutput<typeof calculatorTool>;

    expectTypeOf<{ a: number; b: number }>().toMatchTypeOf<CalcInput>();
    expectTypeOf<{ result: number }>().toMatchTypeOf<CalcOutput>();

    type SearchInput = InferToolInput<typeof searchTool>;
    type SearchOutput = InferToolOutput<typeof searchTool>;

    expectTypeOf<{ query: string }>().toMatchTypeOf<SearchInput>();
    expectTypeOf<{ items: string[] }>().toMatchTypeOf<SearchOutput>();
  });

  it("should extract tool call/result unions from a ToolSet", () => {
    type Calls = TypedToolCall<typeof testTools>;
    type Results = TypedToolResult<typeof testTools>;

    expectTypeOf<Calls>().toEqualTypeOf<TypedToolCall<typeof testTools>>();
    expectTypeOf<Results>().toEqualTypeOf<TypedToolResult<typeof testTools>>();
  });

  it("should allow ToolSet to satisfy exported ToolSet type", () => {
    const tools: ToolSet = testTools;
    expect(tools).toBeDefined();
    expect(typeof tools).toBe("object");
  });
});
