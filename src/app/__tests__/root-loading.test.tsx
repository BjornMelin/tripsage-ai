/** @vitest-environment jsdom */

import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { render } from "@/test/test-utils";
import Loading from "../loading";

describe("Root Loading (loading.tsx)", () => {
  it("renders the skip-link target main landmark", () => {
    render(<Loading />);

    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", MAIN_CONTENT_ID);
    expect(main).toHaveAttribute("tabindex", "-1");
    expect(screen.getByText("Loading TripSage…")).toBeInTheDocument();
  });
});
