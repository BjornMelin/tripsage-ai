import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChatPage from "../page";

describe("ChatPage UI smoke", () => {
  it("renders Stop and Retry controls", () => {
    render(<ChatPage />);
    expect(screen.getByRole("button", { name: /Stop streaming/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Retry last request/i })
    ).toBeInTheDocument();
  });
});
