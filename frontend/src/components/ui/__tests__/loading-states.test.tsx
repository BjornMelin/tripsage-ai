import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import {
  ChatMessageSkeleton,
  ChatLoadingSkeleton,
  SearchResultsSkeleton,
  FormLoadingSkeleton,
  ProfileLoadingSkeleton,
  SettingsLoadingSkeleton,
  AnalyticsCardSkeleton,
  AnalyticsDashboardSkeleton,
  NavigationSkeleton,
  InlineSpinner,
  PageLoadingOverlay,
} from "../loading-states"

describe("ChatMessageSkeleton", () => {
  it("renders message skeleton for assistant", () => {
    render(<ChatMessageSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("renders message skeleton for user with reverse layout", () => {
    render(<ChatMessageSkeleton isUser />)
    
    const container = screen.getAllByRole("status", { hidden: true })[0].closest('.flex')
    expect(container).toHaveClass("flex-row-reverse")
  })
})

describe("ChatLoadingSkeleton", () => {
  it("renders multiple chat messages and typing indicator", () => {
    render(<ChatLoadingSkeleton />)
    
    // Should have multiple message skeletons plus typing indicator
    expect(screen.getByText("Thinking...")).toBeInTheDocument()
    
    // Should have bouncing dots
    const dots = screen.container.querySelectorAll('.animate-bounce')
    expect(dots).toHaveLength(3)
  })
})

describe("SearchResultsSkeleton", () => {
  it("renders default number of results", () => {
    render(<SearchResultsSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    expect(skeletons.length).toBeGreaterThan(10) // Multiple skeletons per result
  })

  it("renders custom number of results", () => {
    render(<SearchResultsSkeleton count={3} />)
    
    // Each result has multiple skeletons, so we check for result containers
    const resultContainers = screen.container.querySelectorAll('.border.rounded-lg')
    expect(resultContainers).toHaveLength(3)
  })
})

describe("FormLoadingSkeleton", () => {
  it("renders form field skeletons", () => {
    render(<FormLoadingSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // Should have skeletons for labels, inputs, and button
    expect(skeletons.length).toBeGreaterThan(5)
  })
})

describe("ProfileLoadingSkeleton", () => {
  it("renders profile components", () => {
    render(<ProfileLoadingSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // Avatar, name, stats, content
    expect(skeletons.length).toBeGreaterThan(8)
  })
})

describe("SettingsLoadingSkeleton", () => {
  it("renders settings sections", () => {
    render(<SettingsLoadingSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // Multiple sections with multiple items each
    expect(skeletons.length).toBeGreaterThan(15)
  })
})

describe("AnalyticsCardSkeleton", () => {
  it("renders analytics card structure", () => {
    render(<AnalyticsCardSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // Title, value, change indicator, icon
    expect(skeletons.length).toBeGreaterThanOrEqual(4)
  })
})

describe("AnalyticsDashboardSkeleton", () => {
  it("renders complete dashboard", () => {
    render(<AnalyticsDashboardSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // KPI cards + charts + table = many skeletons
    expect(skeletons.length).toBeGreaterThan(50)
  })
})

describe("NavigationSkeleton", () => {
  it("renders navigation items", () => {
    render(<NavigationSkeleton />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // 6 nav items × 2 skeletons each (icon + text) = 12
    expect(skeletons).toHaveLength(12)
  })
})

describe("InlineSpinner", () => {
  it("renders with default size", () => {
    render(<InlineSpinner />)
    
    const spinner = screen.getByRole("status")
    expect(spinner).toHaveClass("h-4", "w-4")
    expect(spinner).toHaveAttribute("aria-label", "Loading")
  })

  it("renders with medium size", () => {
    render(<InlineSpinner size="md" />)
    
    const spinner = screen.getByRole("status")
    expect(spinner).toHaveClass("h-6", "w-6")
  })

  it("renders with large size", () => {
    render(<InlineSpinner size="lg" />)
    
    const spinner = screen.getByRole("status")
    expect(spinner).toHaveClass("h-8", "w-8")
  })

  it("applies custom className", () => {
    render(<InlineSpinner className="custom-spinner" />)
    
    const spinner = screen.getByRole("status")
    expect(spinner).toHaveClass("custom-spinner")
  })

  it("has screen reader text", () => {
    render(<InlineSpinner />)
    
    expect(screen.getByText("Loading...")).toBeInTheDocument()
  })
})

describe("PageLoadingOverlay", () => {
  it("renders with default message", () => {
    render(<PageLoadingOverlay />)
    
    expect(screen.getByText("Loading...")).toBeInTheDocument()
    expect(screen.getByRole("status")).toBeInTheDocument()
  })

  it("renders with custom message", () => {
    render(<PageLoadingOverlay message="Processing..." />)
    
    expect(screen.getByText("Processing...")).toBeInTheDocument()
  })

  it("has overlay styling", () => {
    render(<PageLoadingOverlay />)
    
    const overlay = screen.getByText("Loading...").closest('.fixed')
    expect(overlay).toHaveClass("fixed", "inset-0", "z-50")
  })
})