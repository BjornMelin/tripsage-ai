import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { 
  Skeleton, 
  SkeletonText, 
  SkeletonCard, 
  SkeletonAvatar, 
  SkeletonButton, 
  SkeletonTable 
} from "../enhanced-skeleton"

describe("Skeleton", () => {
  it("renders with default props", () => {
    render(<Skeleton />)
    
    const skeleton = screen.getByRole("status")
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveAttribute("aria-label", "Loading...")
    expect(skeleton).toHaveClass("animate-pulse", "bg-muted", "rounded-md")
  })

  it("applies custom className", () => {
    render(<Skeleton className="custom-class" />)
    
    const skeleton = screen.getByRole("status")
    expect(skeleton).toHaveClass("custom-class")
  })

  it("renders with circular variant", () => {
    render(<Skeleton variant="circular" />)
    
    const skeleton = screen.getByRole("status")
    expect(skeleton).toHaveClass("rounded-full")
  })

  it("renders with rectangular variant", () => {
    render(<Skeleton variant="rectangular" />)
    
    const skeleton = screen.getByRole("status")
    expect(skeleton).toHaveClass("rounded-none")
  })

  it("renders with text variant", () => {
    render(<Skeleton variant="text" />)
    
    const skeleton = screen.getByRole("status")
    expect(skeleton).toHaveClass("rounded-sm", "h-4")
  })

  it("applies custom width and height", () => {
    render(<Skeleton width="100px" height="50px" />)
    
    const skeleton = screen.getByRole("status")
    expect(skeleton).toHaveStyle({
      width: "100px",
      height: "50px",
    })
  })

  it("renders multiple skeletons when count > 1", () => {
    render(<Skeleton count={3} />)
    
    const container = screen.getByRole("status")
    expect(container).toBeInTheDocument()
    
    // Should have 3 skeleton divs inside
    const skeletons = container.querySelectorAll("div")
    expect(skeletons).toHaveLength(3)
  })

  it("validates props with schema", () => {
    // Should not throw with valid props
    expect(() => {
      render(<Skeleton variant="circular" count={5} width={100} height={100} />)
    }).not.toThrow()
  })

  it("throws error with invalid count", () => {
    // This would be caught by Zod schema validation
    expect(() => {
      render(<Skeleton count={25} />) // exceeds max of 20
    }).toThrow()
  })
})

describe("SkeletonText", () => {
  it("renders with default lines", () => {
    render(<SkeletonText />)
    
    const lines = screen.getAllByRole("status", { hidden: true })
    expect(lines).toHaveLength(3) // default lines
  })

  it("renders with custom number of lines", () => {
    render(<SkeletonText lines={5} />)
    
    const container = screen.getAllByRole("status", { hidden: true })[0].parentElement
    const lines = container?.querySelectorAll("[role='status']")
    expect(lines).toHaveLength(5)
  })

  it("makes last line shorter", () => {
    render(<SkeletonText lines={2} />)
    
    const lines = screen.getAllByRole("status", { hidden: true })
    expect(lines[0]).toHaveClass("w-full")
    expect(lines[1]).toHaveClass("w-3/4")
  })

  it("applies custom className", () => {
    render(<SkeletonText className="custom-text-class" />)
    
    const container = screen.getAllByRole("status", { hidden: true })[0].parentElement
    expect(container).toHaveClass("custom-text-class")
  })
})

describe("SkeletonCard", () => {
  it("renders card structure", () => {
    render(<SkeletonCard />)
    
    // Should have rectangular skeleton for image and text skeletons
    const skeletons = screen.getAllByRole("status", { hidden: true })
    expect(skeletons.length).toBeGreaterThan(1)
    
    // First skeleton should be rectangular (image)
    expect(skeletons[0]).toHaveClass("h-48", "w-full")
  })

  it("applies custom className", () => {
    render(<SkeletonCard className="custom-card-class" />)
    
    const container = screen.getAllByRole("status", { hidden: true })[0].parentElement
    expect(container).toHaveClass("custom-card-class")
  })
})

describe("SkeletonAvatar", () => {
  it("renders with default medium size", () => {
    render(<SkeletonAvatar />)
    
    const avatar = screen.getByRole("status")
    expect(avatar).toHaveClass("h-12", "w-12", "rounded-full")
  })

  it("renders with small size", () => {
    render(<SkeletonAvatar size="sm" />)
    
    const avatar = screen.getByRole("status")
    expect(avatar).toHaveClass("h-8", "w-8")
  })

  it("renders with large size", () => {
    render(<SkeletonAvatar size="lg" />)
    
    const avatar = screen.getByRole("status")
    expect(avatar).toHaveClass("h-16", "w-16")
  })

  it("applies custom className", () => {
    render(<SkeletonAvatar className="custom-avatar-class" />)
    
    const avatar = screen.getByRole("status")
    expect(avatar).toHaveClass("custom-avatar-class")
  })
})

describe("SkeletonButton", () => {
  it("renders with default button dimensions", () => {
    render(<SkeletonButton />)
    
    const button = screen.getByRole("status")
    expect(button).toHaveClass("h-10", "w-24", "rounded-md")
  })

  it("applies custom className", () => {
    render(<SkeletonButton className="custom-button-class" />)
    
    const button = screen.getByRole("status")
    expect(button).toHaveClass("custom-button-class")
  })
})

describe("SkeletonTable", () => {
  it("renders with default rows and columns", () => {
    render(<SkeletonTable />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // Default: 5 rows × 4 columns + 1 header row × 4 columns = 24 total
    expect(skeletons).toHaveLength(24)
  })

  it("renders with custom rows and columns", () => {
    render(<SkeletonTable rows={3} columns={2} />)
    
    const skeletons = screen.getAllByRole("status", { hidden: true })
    // 3 rows × 2 columns + 1 header row × 2 columns = 8 total
    expect(skeletons).toHaveLength(8)
  })

  it("applies custom className", () => {
    render(<SkeletonTable className="custom-table-class" />)
    
    const container = screen.getAllByRole("status", { hidden: true })[0].closest('[class*="space-y"]')
    expect(container).toHaveClass("custom-table-class")
  })
})