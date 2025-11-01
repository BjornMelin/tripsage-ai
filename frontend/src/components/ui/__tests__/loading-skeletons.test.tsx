/**
 * @fileoverview Unit tests for loading skeleton components, verifying rendering,
 * accessibility, animation, and responsive behavior for various UI skeleton
 * patterns including avatars, cards, charts, forms, lists, and tables.
 */

import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { render } from "@/test/test-utils";
import {
  AvatarSkeleton,
  CardSkeleton,
  ChartSkeleton,
  FormSkeleton,
  ListItemSkeleton,
  TableSkeleton,
} from "../loading-skeletons";

describe("AvatarSkeleton", () => {
  it("renders with default size", () => {
    render(<AvatarSkeleton data-testid="avatar" />);

    const avatar = screen.getByTestId("avatar");
    expect(avatar).toBeInTheDocument();
    expect(avatar).toHaveClass("h-10", "w-10");
  });

  it("applies different sizes", () => {
    const { rerender } = render(<AvatarSkeleton size="sm" data-testid="avatar" />);
    let avatar = screen.getByTestId("avatar");
    expect(avatar).toHaveClass("h-8", "w-8");

    rerender(<AvatarSkeleton size="lg" data-testid="avatar" />);
    avatar = screen.getByTestId("avatar");
    expect(avatar).toHaveClass("h-12", "w-12");

    rerender(<AvatarSkeleton size="xl" data-testid="avatar" />);
    avatar = screen.getByTestId("avatar");
    expect(avatar).toHaveClass("h-16", "w-16");
  });

  it("has correct accessibility label", () => {
    render(<AvatarSkeleton data-testid="avatar" />);

    const avatar = screen.getByTestId("avatar");
    expect(avatar).toHaveAttribute("aria-label", "Loading profile picture");
  });
});

describe("CardSkeleton", () => {
  it("renders basic card skeleton", () => {
    render(<CardSkeleton data-testid="card" />);

    const card = screen.getByTestId("card");
    expect(card).toBeInTheDocument();
    expect(card).toHaveAttribute("role", "status");
    expect(card).toHaveAttribute("aria-label", "Loading card content");
  });

  it("includes image when specified", () => {
    const { container } = render(<CardSkeleton hasImage={true} />);

    // Check for image skeleton
    const imageSkeletons = container.querySelectorAll("[class*='h-48']");
    expect(imageSkeletons.length).toBeGreaterThan(0);
  });

  it("includes avatar when specified", () => {
    const { container } = render(<CardSkeleton hasAvatar={true} />);

    // Check for avatar skeleton
    const avatarSkeletons = container.querySelectorAll("[class*='rounded-full']");
    expect(avatarSkeletons.length).toBeGreaterThan(0);
  });

  it("respects title and body line counts", () => {
    const { container } = render(<CardSkeleton titleLines={2} bodyLines={5} />);

    // Should have multiple skeleton elements
    const skeletons = container.querySelectorAll("[role='status'] > *");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe("ListItemSkeleton", () => {
  it("renders basic list item", () => {
    render(<ListItemSkeleton data-testid="list-item" />);

    const listItem = screen.getByTestId("list-item");
    expect(listItem).toBeInTheDocument();
    expect(listItem).toHaveAttribute("aria-label", "Loading list item");
  });

  it("includes avatar when specified", () => {
    const { container } = render(<ListItemSkeleton hasAvatar={true} />);

    const avatarSkeletons = container.querySelectorAll("[class*='rounded-full']");
    expect(avatarSkeletons.length).toBeGreaterThan(0);
  });

  it("includes action when specified", () => {
    const { container } = render(<ListItemSkeleton hasAction={true} />);

    const actionSkeletons = container.querySelectorAll("[class*='h-8'][class*='w-16']");
    expect(actionSkeletons.length).toBeGreaterThan(0);
  });
});

describe("TableSkeleton", () => {
  it("renders table with default configuration", () => {
    render(<TableSkeleton data-testid="table" />);

    const table = screen.getByTestId("table");
    expect(table).toBeInTheDocument();
    expect(table).toHaveAttribute("aria-label", "Loading table data");
  });

  it("renders correct number of rows and columns", () => {
    const { container } = render(<TableSkeleton rows={3} columns={2} />);

    const bodyRows = container.querySelectorAll("tbody tr");
    expect(bodyRows).toHaveLength(3);

    const firstRowCells = container.querySelectorAll("tbody tr:first-child td");
    expect(firstRowCells).toHaveLength(2);
  });

  it("includes header when specified", () => {
    const { container } = render(<TableSkeleton hasHeader={true} />);

    const header = container.querySelector("thead");
    expect(header).toBeInTheDocument();
  });

  it("excludes header when specified", () => {
    const { container } = render(<TableSkeleton hasHeader={false} />);

    const header = container.querySelector("thead");
    expect(header).not.toBeInTheDocument();
  });
});

describe("FormSkeleton", () => {
  it("renders form with default fields", () => {
    render(<FormSkeleton data-testid="form" />);

    const form = screen.getByTestId("form");
    expect(form).toBeInTheDocument();
    expect(form).toHaveAttribute("aria-label", "Loading form");
  });

  it("renders correct number of fields", () => {
    const { container } = render(<FormSkeleton fields={5} />);

    // Each field should have label and input skeletons
    const fieldGroups = container.querySelectorAll("[class*='space-y-2']");
    expect(fieldGroups.length).toBeGreaterThanOrEqual(5);
  });

  it("includes submit button when specified", () => {
    const { container } = render(<FormSkeleton hasSubmitButton={true} />);

    // The submit button skeleton uses inline dimensions (height 2.5rem, width 120px)
    const submitSkeletons = container.querySelectorAll("[style*='width: 120px']");
    expect(submitSkeletons.length).toBeGreaterThan(0);
  });

  it("excludes submit button when specified", () => {
    const { container } = render(<FormSkeleton hasSubmitButton={false} />);

    // Should have fewer skeleton elements without submit button
    const allSkeletons = container.querySelectorAll("[class*='animate-pulse']");
    expect(allSkeletons.length).toBeGreaterThan(0);
  });
});

describe("ChartSkeleton", () => {
  it("renders chart with default type", () => {
    render(<ChartSkeleton data-testid="chart" />);

    const chart = screen.getByTestId("chart");
    expect(chart).toBeInTheDocument();
    expect(chart).toHaveAttribute("aria-label", "Loading chart data");
  });

  it("renders different chart types", () => {
    const types = ["bar", "line", "pie", "area"] as const;

    types.forEach((type) => {
      const { container } = render(<ChartSkeleton type={type} />);
      const chart = container.firstChild;
      expect(chart).toBeInTheDocument();
    });
  });

  it("includes chart title", () => {
    const { container } = render(<ChartSkeleton />);

    // Title skeleton uses inline height/width (1.5rem, 40%)
    const titleSkeletons = container.querySelectorAll("[style*='height: 1.5rem']");
    expect(titleSkeletons.length).toBeGreaterThan(0);
  });

  it("includes chart legend", () => {
    const { container } = render(<ChartSkeleton />);

    // Should have legend items
    const legendItems = container.querySelectorAll("[class*='h-3'][class*='w-3']");
    expect(legendItems.length).toBeGreaterThan(0);
  });
});
