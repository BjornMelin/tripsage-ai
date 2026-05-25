/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { copyTextToClipboard, copyToClipboardWithToast } from "@/lib/client/clipboard";

const { mockRecordClientErrorOnActiveSpan } = vi.hoisted(() => ({
  mockRecordClientErrorOnActiveSpan: vi.fn(),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
}));

const ORIGINAL_CLIPBOARD_DESCRIPTOR = Object.getOwnPropertyDescriptor(
  navigator,
  "clipboard"
);
const ORIGINAL_EXEC_COMMAND_DESCRIPTOR = Object.getOwnPropertyDescriptor(
  document,
  "execCommand"
);

function restoreProperty<T extends object>(
  target: T,
  property: keyof T,
  descriptor: PropertyDescriptor | undefined
): void {
  if (descriptor) {
    Object.defineProperty(target, property, descriptor);
    return;
  }

  Reflect.deleteProperty(target, property);
}

function mockClipboardWriteText(writeText: (text: string) => Promise<void>): void {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
}

function mockExecCommand(result: boolean): void {
  Object.defineProperty(document, "execCommand", {
    configurable: true,
    value: vi.fn(() => result),
  });
}

describe("clipboard client helpers", () => {
  beforeEach(() => {
    mockRecordClientErrorOnActiveSpan.mockReset();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    restoreProperty(navigator, "clipboard", ORIGINAL_CLIPBOARD_DESCRIPTOR);
    restoreProperty(document, "execCommand", ORIGINAL_EXEC_COMMAND_DESCRIPTOR);
    vi.restoreAllMocks();
  });

  it("copies text through the Clipboard API when available", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    mockClipboardWriteText(writeText);

    await expect(copyTextToClipboard("share link")).resolves.toEqual({
      method: "clipboard",
      ok: true,
    });
    expect(writeText).toHaveBeenCalledWith("share link");
    expect(mockRecordClientErrorOnActiveSpan).not.toHaveBeenCalled();
  });

  it("falls back to execCommand when Clipboard API writes fail", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("clipboard unavailable"));
    mockClipboardWriteText(writeText);
    mockExecCommand(true);

    await expect(copyTextToClipboard("fallback link")).resolves.toEqual({
      method: "fallback",
      ok: true,
    });
    expect(document.execCommand).toHaveBeenCalledWith("copy");
    expect(mockRecordClientErrorOnActiveSpan).not.toHaveBeenCalled();
  });

  it("reports generic copy failures through telemetry while preserving toast feedback", async () => {
    const copyError = new Error("clipboard failed");
    const writeText = vi.fn().mockRejectedValue(copyError);
    const toast = vi.fn();
    mockClipboardWriteText(writeText);
    mockExecCommand(false);

    await expect(copyToClipboardWithToast("broken link", toast)).resolves.toEqual({
      error: copyError,
      ok: false,
      reason: "failed",
    });
    expect(toast).toHaveBeenCalledWith({
      description: "Unable to copy. Please copy it manually.",
      title: "Copy Failed",
      variant: "destructive",
    });
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(copyError, {
      action: "copyTextToClipboard",
      context: "clipboard",
      reason: "failed",
    });
  });
});
