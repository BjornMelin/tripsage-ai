/**
 * @fileoverview Tests for Message component, verifying user and assistant message rendering with different variants.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/ai-elements/message";

/** Test suite for Message component */
describe("ai-elements/message", () => {
  /** Test that a user message with contained variant is rendered by default */
  it("renders a user message with contained variant by default", () => {
    render(
      <Message from="user">
        <MessageContent>Hi there!</MessageContent>
        <MessageAvatar name="Alex" src="" />
      </Message>
    );
    const content = screen.getByText("Hi there!");
    expect(content).toBeInTheDocument();
    const wrapper = content.closest(".is-user");
    expect(wrapper).not.toBeNull();
  });

  /** Test that an assistant message with flat variant is rendered */
  it("renders assistant message with flat variant", () => {
    render(
      <Message from="assistant">
        <MessageContent variant="flat">Hello! How can I help you?</MessageContent>
        <MessageAvatar name="AI" src="" />
      </Message>
    );
    expect(screen.getByText(/How can I help/)).toBeInTheDocument();
  });
});
