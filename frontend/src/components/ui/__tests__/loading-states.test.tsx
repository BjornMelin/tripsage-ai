import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { 
  LoadingOverlay, 
  LoadingState, 
  LoadingButton, 
  LoadingContainer, 
  PageLoading 
} from "../loading-states";

describe("LoadingOverlay", () => {
  it("does not render when not visible", () => {
    const { container } = render(<LoadingOverlay isVisible={false} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders when visible", () => {
    render(<LoadingOverlay isVisible={true} data-testid="overlay" />);
    
    const overlay = screen.getByTestId("overlay");
    expect(overlay).toBeInTheDocument();
    expect(overlay).toHaveAttribute("role", "status");
  });

  it("displays message", () => {
    render(<LoadingOverlay isVisible={true} message="Loading data..." />);
    
    expect(screen.getByText("Loading data...")).toBeInTheDocument();
  });

  it("displays progress bar", () => {
    render(<LoadingOverlay isVisible={true} progress={50} />);
    
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText("Progress")).toBeInTheDocument();
  });

  it("applies backdrop by default", () => {
    render(<LoadingOverlay isVisible={true} data-testid="overlay" />);
    
    const overlay = screen.getByTestId("overlay");
    expect(overlay).toHaveClass("bg-background/80", "backdrop-blur-sm");
  });

  it("can disable backdrop", () => {
    render(<LoadingOverlay isVisible={true} backdrop={false} data-testid="overlay" />);
    
    const overlay = screen.getByTestId("overlay");
    expect(overlay).not.toHaveClass("bg-background/80", "backdrop-blur-sm");
  });
});

describe("LoadingState", () => {
  it("shows children when not loading", () => {
    render(
      <LoadingState isLoading={false}>
        <div>Content</div>
      </LoadingState>
    );
    
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("shows spinner when loading", () => {
    render(
      <LoadingState isLoading={true}>
        <div>Content</div>
      </LoadingState>
    );
    
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
    // Check for spinner presence
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows skeleton when provided", () => {
    render(
      <LoadingState isLoading={true} skeleton={<div data-testid="skeleton">Skeleton</div>}>
        <div>Content</div>
      </LoadingState>
    );
    
    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
  });

  it("shows fallback when provided", () => {
    render(
      <LoadingState isLoading={true} fallback={<div data-testid="fallback">Fallback</div>}>
        <div>Content</div>
      </LoadingState>
    );
    
    expect(screen.getByTestId("fallback")).toBeInTheDocument();
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
  });
});

describe("LoadingButton", () => {
  it("renders children when not loading", () => {
    render(<LoadingButton>Click me</LoadingButton>);
    
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("shows loading text when loading", () => {
    render(
      <LoadingButton isLoading={true} loadingText="Saving...">
        Click me
      </LoadingButton>
    );
    
    expect(screen.getByText("Saving...")).toBeInTheDocument();
    expect(screen.queryByText("Click me")).not.toBeInTheDocument();
  });

  it("is disabled when loading", () => {
    render(
      <LoadingButton isLoading={true}>
        Click me
      </LoadingButton>
    );
    
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveClass("cursor-not-allowed", "opacity-70");
  });

  it("handles click events when not loading", () => {
    const handleClick = vi.fn();
    render(
      <LoadingButton onClick={handleClick}>
        Click me
      </LoadingButton>
    );
    
    const button = screen.getByRole("button");
    fireEvent.click(button);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("respects disabled prop", () => {
    render(
      <LoadingButton disabled>
        Click me
      </LoadingButton>
    );
    
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });
});

describe("LoadingContainer", () => {
  it("shows children when not loading", () => {
    render(
      <LoadingContainer isLoading={false}>
        <div>Content</div>
      </LoadingContainer>
    );
    
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("shows loading spinner when loading", () => {
    render(
      <LoadingContainer isLoading={true}>
        <div>Content</div>
      </LoadingContainer>
    );
    
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("displays loading message", () => {
    render(
      <LoadingContainer isLoading={true} loadingMessage="Loading data...">
        <div>Content</div>
      </LoadingContainer>
    );
    
    expect(screen.getByText("Loading data...")).toBeInTheDocument();
  });

  it("applies minimum height", () => {
    render(
      <LoadingContainer isLoading={false} minHeight="400px" data-testid="container">
        <div>Content</div>
      </LoadingContainer>
    );
    
    const container = screen.getByTestId("container");
    expect(container).toHaveStyle({ minHeight: "400px" });
  });

  it("applies numeric minimum height", () => {
    render(
      <LoadingContainer isLoading={false} minHeight={300} data-testid="container">
        <div>Content</div>
      </LoadingContainer>
    );
    
    const container = screen.getByTestId("container");
    expect(container).toHaveStyle({ minHeight: "300px" });
  });
});

describe("PageLoading", () => {
  it("renders with default message", () => {
    render(<PageLoading />);
    
    expect(screen.getByText("Loading page...")).toBeInTheDocument();
  });

  it("renders with custom message", () => {
    render(<PageLoading message="Loading application..." />);
    
    expect(screen.getByText("Loading application...")).toBeInTheDocument();
  });

  it("displays progress bar", () => {
    render(<PageLoading progress={75} />);
    
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("Loading")).toBeInTheDocument();
  });

  it("has correct accessibility attributes", () => {
    render(<PageLoading message="Loading app..." />);
    
    const loading = screen.getByRole("status");
    expect(loading).toHaveAttribute("aria-live", "polite");
    expect(loading).toHaveAttribute("aria-label", "Loading app...");
  });

  it("applies custom className", () => {
    render(<PageLoading className="custom-loading" data-testid="page-loading" />);
    
    const loading = screen.getByTestId("page-loading");
    expect(loading).toHaveClass("custom-loading");
  });
});