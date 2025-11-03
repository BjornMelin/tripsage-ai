/**
 * @fileoverview Tests for Conversation component, verifying empty state rendering and message display.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
} from "@/components/ai-elements/conversation";

/** Test suite for Conversation component */
describe("ai-elements/conversation", () => {
  /** Test that the empty state is rendered when no messages exist */  
  it("renders empty state when no messages", () => {
    render(
      <Conversation>
        <ConversationContent>
          <ConversationEmptyState title="Start a conversation" />
        </ConversationContent>
      </Conversation>
    );
    expect(screen.getByText("Start a conversation")).toBeInTheDocument();
  });

  /** Test that the provided children are rendered when messages exist */
  it("renders provided children when messages exist", () => {
    render(
      <Conversation>
        <ConversationContent>
          <div>Message A</div>
        </ConversationContent>
      </Conversation>
    );
    expect(screen.getByText("Message A")).toBeInTheDocument();
  });
});

