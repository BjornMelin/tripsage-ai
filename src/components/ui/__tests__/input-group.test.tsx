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
});
