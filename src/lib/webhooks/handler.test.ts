import { describe, expect, it } from "vitest";
import { classifyError } from "@/lib/webhooks/handler";

const makeError = (message: string, name = "Error") => {
  const err = new Error(message);
  err.name = name;
  return err;
};

describe("classifyError heuristics", () => {
  it("classifies validation-like messages as VALIDATION_ERROR", () => {
    expect(classifyError(makeError("value must be a string", "TypeError"))).toEqual({
      code: "VALIDATION_ERROR",
      status: 400,
    });
    expect(classifyError(makeError("Invalid payload", "ValidationError"))).toEqual({
      code: "VALIDATION_ERROR",
      status: 400,
    });
  });

  it("classifies not found messages as NOT_FOUND", () => {
    expect(classifyError(makeError("Resource does not exist"))).toEqual({
      code: "NOT_FOUND",
      status: 404,
    });
  });

  it("classifies duplicate/conflict messages as CONFLICT", () => {
    expect(classifyError(makeError("Record already exists"))).toEqual({
      code: "CONFLICT",
      status: 409,
    });
  });

  it("classifies service unavailable messages as SERVICE_UNAVAILABLE", () => {
    expect(
      classifyError(makeError("Service unavailable, retry later", "ServiceError"))
    ).toEqual({
      code: "SERVICE_UNAVAILABLE",
      status: 503,
    });
  });

  it("classifies timeout messages as TIMEOUT", () => {
    expect(classifyError(makeError("Request timed out", "TimeoutError"))).toEqual({
      code: "TIMEOUT",
      status: 504,
    });
  });

  it("defaults to UNKNOWN for unmatched errors", () => {
    expect(classifyError(makeError("Unexpected failure"))).toEqual({
      code: "UNKNOWN",
      status: 500,
    });
  });
});
