/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { safeHref } from "../safe-href";

describe("safeHref", () => {
  it("allows http/https/mailto URLs", () => {
    expect(safeHref("https://example.com")).toBe("https://example.com");
    expect(safeHref("http://example.com/a")).toBe("http://example.com/a");
    expect(safeHref("mailto:test@example.com")).toBe("mailto:test@example.com");
  });

  it("allows absolute paths", () => {
    expect(safeHref("/docs/guide")).toBe("/docs/guide");
  });

  it("blocks protocol-relative and unsafe schemes", () => {
    expect(safeHref("//evil.com")).toBeUndefined();
    expect(safeHref("javascript:alert(1)")).toBeUndefined();
    expect(
      safeHref("data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==")
    ).toBeUndefined();
    expect(safeHref("file:///etc/passwd")).toBeUndefined();
  });

  it("returns undefined for empty or malformed values", () => {
    expect(safeHref("")).toBeUndefined();
    expect(safeHref("   ")).toBeUndefined();
    expect(safeHref("not a url")).toBeUndefined();
  });
});
