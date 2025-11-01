/**
 * @fileoverview Conversation primitives used to render a scrollable chat area
 * that sticks to the bottom as new messages stream in. Built on
 * `use-stick-to-bottom` and compatible with AI Elements message components.
 */
"use client";

import { ArrowDownIcon } from "lucide-react";
import type { ComponentProps } from "react";
import { useCallback } from "react";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Props for the Conversation container. */
export type ConversationProps = ComponentProps<typeof StickToBottom>;

/**
 * Conversation container that auto-sticks to the bottom as content grows.
 *
 * @param className Optional extra classes.
 * @param props Additional StickToBottom props.
 * @returns A scrollable region with ARIA `role="log"`.
 */
export const Conversation = ({ className, ...props }: ConversationProps) => (
  <StickToBottom
    className={cn("relative flex-1 overflow-y-auto", className)}
    initial="smooth"
    resize="smooth"
    role="log"
    {...props}
  />
);

/** Props for the Conversation content region. */
export type ConversationContentProps = ComponentProps<typeof StickToBottom.Content>;

/**
 * The inner content region of the conversation.
 *
 * @param className Optional extra classes.
 * @param props Additional content props.
 * @returns A padded content wrapper.
 */
export const ConversationContent = ({
  className,
  ...props
}: ConversationContentProps) => (
  <StickToBottom.Content className={cn("p-4", className)} {...props} />
);

/** Props for the empty state rendered when there are no messages. */
export type ConversationEmptyStateProps = ComponentProps<"div"> & {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
};

/**
 * A simple empty state to display when no messages exist.
 *
 * @param title Optional title text.
 * @param description Optional message describing the state.
 * @param icon Optional icon React node.
 * @returns A centered placeholder UI.
 */
export const ConversationEmptyState = ({
  className,
  title = "No messages yet",
  description = "Start a conversation to see messages here",
  icon,
  children,
  ...props
}: ConversationEmptyStateProps) => (
  <div
    className={cn(
      "flex size-full flex-col items-center justify-center gap-3 p-8 text-center",
      className
    )}
    {...props}
  >
    {children ?? (
      <>
        {icon && <div className="text-muted-foreground">{icon}</div>}
        <div className="space-y-1">
          <h3 className="font-medium text-sm">{title}</h3>
          {description && (
            <p className="text-muted-foreground text-sm">{description}</p>
          )}
        </div>
      </>
    )}
  </div>
);

/** Props for the floating scroll-to-bottom button. */
export type ConversationScrollButtonProps = ComponentProps<typeof Button>;

/**
 * Renders a floating button that appears when scrolled away from bottom and
 * scrolls back to the latest message on click.
 *
 * @param className Optional extra classes.
 * @param props Additional button props.
 * @returns The scroll button when needed; otherwise `null`.
 */
export const ConversationScrollButton = ({
  className,
  ...props
}: ConversationScrollButtonProps) => {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();

  const handleScrollToBottom = useCallback(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  return (
    !isAtBottom && (
      <Button
        className={cn(
          "absolute bottom-4 left-[50%] translate-x-[-50%] rounded-full",
          className
        )}
        onClick={handleScrollToBottom}
        size="icon"
        type="button"
        variant="outline"
        {...props}
      >
        <ArrowDownIcon className="size-4" />
      </Button>
    )
  );
};
