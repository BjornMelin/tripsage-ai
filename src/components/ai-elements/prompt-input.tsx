/**
 * @fileoverview Prompt input primitives for chat UIs.
 */

"use client";

import type { ChatStatus } from "ai";
import { Loader2Icon, SendIcon, SquareIcon, XIcon } from "lucide-react";
import type {
  ComponentProps,
  FormEvent,
  FormEventHandler,
  HTMLAttributes,
  KeyboardEventHandler,
} from "react";
import { useState } from "react";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { cn } from "@/lib/utils";

/**
 * Message data structure for prompt submissions.
 *
 * Keep this minimal; richer message shapes live at the chat transport layer.
 */
export type PromptInputMessage = {
  /** Optional text content of the message. */
  text?: string;
};

/**
 * Props for the PromptInput form wrapper.
 */
export type PromptInputProps = Omit<HTMLAttributes<HTMLFormElement>, "onSubmit"> & {
  /** Submit handler for the prompt input. */
  onSubmit: (
    message: PromptInputMessage,
    event: FormEvent<HTMLFormElement>
  ) => void | Promise<void>;
  /** Optional error handler for submission failures or validation errors. */
  onError?: (error: Error) => void;
};

/**
 * Form wrapper that provides consistent layout via `InputGroup`.
 */
export const PromptInput = ({
  className,
  onSubmit,
  onError,
  children,
  ...props
}: PromptInputProps) => {
  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const message = formData.get("message");
    const text = typeof message === "string" ? message : "";
    const trimmed = text.trim();

    // Validate non-empty message before submission
    if (trimmed.length === 0) {
      const error = new Error("Cannot submit empty message");
      if (process.env.NODE_ENV === "development") {
        console.error("PromptInput validation error:", error);
      }
      onError?.(error);
      return;
    }

    try {
      const result = onSubmit({ text: trimmed }, event);

      if (result instanceof Promise) {
        result
          .then(() => {
            form.reset();
          })
          .catch((error) => {
            if (process.env.NODE_ENV === "development") {
              console.error("PromptInput submission error:", error);
            }
            onError?.(error instanceof Error ? error : new Error(String(error)));
          });
      } else {
        form.reset();
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      if (process.env.NODE_ENV === "development") {
        console.error("PromptInput submission error:", err);
      }
      onError?.(err);
    }
  };

  return (
    <form className={cn("w-full", className)} onSubmit={handleSubmit} {...props}>
      <InputGroup>{children}</InputGroup>
    </form>
  );
};

export type PromptInputBodyProps = HTMLAttributes<HTMLDivElement>;

/**
 * Semantic container for the main content area of the prompt input.
 */
export const PromptInputBody = ({ className, ...props }: PromptInputBodyProps) => (
  <div className={cn("contents", className)} {...props} />
);

export type PromptInputHeaderProps = Omit<
  ComponentProps<typeof InputGroupAddon>,
  "align"
>;

/**
 * Layout component for header content above the input area.
 */
export const PromptInputHeader = ({ className, ...props }: PromptInputHeaderProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("order-first flex-wrap gap-1", className)}
    {...props}
  />
);

export type PromptInputFooterProps = Omit<
  ComponentProps<typeof InputGroupAddon>,
  "align"
>;

/**
 * Layout component for footer content below the input area.
 */
export const PromptInputFooter = ({ className, ...props }: PromptInputFooterProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("justify-between gap-1", className)}
    {...props}
  />
);

export type PromptInputTextareaProps = ComponentProps<typeof InputGroupTextarea> & {
  /** Placeholder text for the textarea. */
  placeholder?: string;
};

/**
 * Textarea component with Enter-to-submit handling (Shift+Enter inserts a newline).
 */
export const PromptInputTextarea = ({
  className,
  placeholder = "What would you like to know?",
  ...props
}: PromptInputTextareaProps) => {
  const [isComposing, setIsComposing] = useState(false);

  const handleKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (event.key !== "Enter") {
      return;
    }
    if (isComposing || event.nativeEvent.isComposing) {
      return;
    }
    if (event.shiftKey) {
      return;
    }

    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  };

  return (
    <InputGroupTextarea
      className={cn("field-sizing-content max-h-48 min-h-16", className)}
      name="message"
      onCompositionEnd={() => setIsComposing(false)}
      onCompositionStart={() => setIsComposing(true)}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      {...props}
    />
  );
};

export type PromptInputSubmitProps = ComponentProps<typeof InputGroupButton> & {
  /** Current chat status to determine icon display. */
  status?: ChatStatus;
};

/**
 * Status-aware submit button for prompt forms.
 */
export const PromptInputSubmit = ({
  className,
  variant = "default",
  size = "icon-sm",
  status,
  children,
  ...props
}: PromptInputSubmitProps) => {
  let icon = <SendIcon className="size-4" />;

  if (status === "submitted") {
    icon = <Loader2Icon className="size-4 animate-spin" />;
  } else if (status === "streaming") {
    icon = <SquareIcon className="size-4" />;
  } else if (status === "error") {
    icon = <XIcon className="size-4" />;
  }

  return (
    <InputGroupButton
      aria-label="Submit"
      className={cn(className)}
      size={size}
      type="submit"
      variant={variant}
      {...props}
    >
      {children ?? icon}
    </InputGroupButton>
  );
};
