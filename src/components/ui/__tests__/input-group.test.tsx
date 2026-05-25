/** @vitest-environment jsdom */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";

describe("InputGroup", () => {
  it("keeps addons out of button navigation while preserving pointer focus", () => {
    render(
      <InputGroup>
        <InputGroupAddon data-testid="input-addon">Prefix</InputGroupAddon>
        <InputGroupInput aria-label="Destination" />
      </InputGroup>
    );

    expect(screen.queryByRole("button", { name: "Prefix" })).toBeNull();

    const input = screen.getByRole("textbox", { name: "Destination" });
    fireEvent.mouseDown(screen.getByTestId("input-addon"));

    expect(document.activeElement).toBe(input);
  });

  it("does not forward focus when the addon target is a nested button", () => {
    render(
      <InputGroup>
        <InputGroupAddon>
          <button type="button">Action</button>
        </InputGroupAddon>
        <InputGroupInput aria-label="Destination" />
      </InputGroup>
    );

    const button = screen.getByRole("button", { name: "Action" });
    const input = screen.getByRole("textbox", { name: "Destination" });
    button.focus();

    fireEvent.mouseDown(button);

    expect(document.activeElement).not.toBe(input);
    expect(document.activeElement).toBe(button);
  });
});
