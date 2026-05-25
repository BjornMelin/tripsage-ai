/** @vitest-environment jsdom */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";

const { mockRecordClientErrorOnActiveSpan } = vi.hoisted(() => ({
  mockRecordClientErrorOnActiveSpan: vi.fn(),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
}));

/** Test suite for PromptInput component */
describe("ai-elements/prompt-input", () => {
  beforeEach(() => {
    vi.useRealTimers();
    mockRecordClientErrorOnActiveSpan.mockReset();
  });

  const renderPromptInput = ({
    onError,
    onSubmit,
  }: {
    onError?: (error: Error) => void;
    onSubmit: ComponentProps<typeof PromptInput>["onSubmit"];
  }) => {
    render(
      <PromptInput onSubmit={onSubmit} onError={onError}>
        <PromptInputBody>
          <PromptInputTextarea placeholder="Type here" />
        </PromptInputBody>
        <PromptInputFooter>
          <PromptInputSubmit>Send</PromptInputSubmit>
        </PromptInputFooter>
      </PromptInput>
    );
  };

  const getPromptForm = () => {
    const submit = screen.getByText("Send");
    const form = submit.closest("form");
    expect(form).not.toBeNull();

    if (!form) {
      throw new Error("Expected prompt form to be present");
    }

    return form;
  };

  /** Test that onSubmit is called with typed text when submitted */
  it("calls onSubmit with typed text when submitted", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderPromptInput({ onSubmit });

    const textarea = screen.getByPlaceholderText("Type here") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Hello AI" } });

    // Submit the form by clicking the submit button
    fireEvent.submit(getPromptForm());

    await Promise.resolve();
    expect(onSubmit).toHaveBeenCalledTimes(1);

    const payload = onSubmit.mock.calls[0]?.[0];
    expect(payload?.text).toBe("Hello AI");
  });

  it("reports empty prompt validation errors through telemetry", () => {
    const onError = vi.fn();
    const onSubmit = vi.fn();

    renderPromptInput({ onError, onSubmit });

    fireEvent.submit(getPromptForm());

    expect(onSubmit).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(expect.any(Error));
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(expect.any(Error), {
      action: "validate",
      context: "PromptInput",
    });
  });

  it("reports async submission failures through telemetry", async () => {
    const onError = vi.fn();
    const error = new Error("stream unavailable");
    const onSubmit = vi.fn().mockRejectedValue(error);

    renderPromptInput({ onError, onSubmit });

    const textarea = screen.getByPlaceholderText("Type here") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Plan a trip" } });
    fireEvent.submit(getPromptForm());

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(error);
    });
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(error, {
      action: "submit",
      context: "PromptInput",
    });
  });
});
