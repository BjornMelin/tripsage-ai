/** @vitest-environment jsdom */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";

/** Test suite for PromptInput component */
describe("ai-elements/prompt-input", () => {
  /** Test that onSubmit is called with typed text when submitted */
  it(
    "calls onSubmit with typed text when submitted",
    async () => {
      const onSubmit = vi.fn().mockResolvedValue(undefined);
      render(
        <PromptInput onSubmit={onSubmit}>
          <PromptInputBody>
            <PromptInputTextarea placeholder="Type here" />
          </PromptInputBody>
          <PromptInputFooter>
            <PromptInputSubmit>Send</PromptInputSubmit>
          </PromptInputFooter>
        </PromptInput>
      );

      const textarea = screen.getByPlaceholderText("Type here") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "Hello AI" } });

      // Submit the form by clicking the submit button
      const submit = screen.getByText("Send");
      const form = submit.closest("form");
      expect(form).toBeInTheDocument();
      
      fireEvent.submit(form!);

      await waitFor(
        () => {
          expect(onSubmit).toHaveBeenCalled();
        },
        { timeout: 2000 }
      );
      
      const payload = onSubmit.mock.calls[0]?.[0];
      expect(payload?.text).toBe("Hello AI");
    },
    10000
  );
});
