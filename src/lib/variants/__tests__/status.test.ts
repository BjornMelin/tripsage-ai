import { describe, expect, it } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { getToneColors, statusVariants } from "../status";

describe("statusVariants", () => {
  describe("urgency variants", () => {
    it("returns high urgency classes", () => {
      const result = statusVariants({ urgency: "high" });
      expect(result).toContain("bg-destructive/10");
      expect(result).toContain("text-destructive");
      expect(result).toContain("ring-destructive/20");
    });

    it("returns medium urgency classes", () => {
      const result = statusVariants({ urgency: "medium" });
      expect(result).toContain("bg-warning/10");
      expect(result).toContain("text-warning");
      expect(result).toContain("ring-warning/20");
    });

    it("returns low urgency classes", () => {
      const result = statusVariants({ urgency: "low" });
      expect(result).toContain("bg-success/10");
      expect(result).toContain("text-success");
      expect(result).toContain("ring-success/20");
    });
  });

  describe("status variants", () => {
    it("returns active status classes", () => {
      const result = statusVariants({ status: "active" });
      expect(result).toContain("bg-success/10");
      expect(result).toContain("text-success");
      expect(result).toContain("ring-success/20");
    });

    it("returns error status classes", () => {
      const result = statusVariants({ status: "error" });
      expect(result).toContain("bg-destructive/10");
      expect(result).toContain("text-destructive");
      expect(result).toContain("ring-destructive/20");
    });

    it("returns pending status classes", () => {
      const result = statusVariants({ status: "pending" });
      expect(result).toContain("bg-warning/10");
      expect(result).toContain("text-warning");
      expect(result).toContain("ring-warning/20");
    });

    it("returns info status classes", () => {
      const result = statusVariants({ status: "info" });
      expect(result).toContain("bg-info/10");
      expect(result).toContain("text-info");
      expect(result).toContain("ring-info/20");
    });
  });

  describe("default behavior", () => {
    it("returns base classes with no variants", () => {
      const result = statusVariants({});
      expect(result).toContain("inline-flex");
      expect(result).toContain("items-center");
      expect(result).toContain("rounded-md");
      expect(result).toContain("px-2");
      expect(result).toContain("py-1");
      expect(result).toContain("text-xs");
      expect(result).toContain("font-medium");
      expect(result).toContain("ring-1");
      expect(result).toContain("ring-inset");
    });

    it("falls back to unknown tone for invalid values", () => {
      const result = statusVariants({ tone: unsafeCast<never>("invalid") });
      expect(result).toContain("bg-muted");
      expect(result).toContain("text-muted-foreground");
      expect(result).toContain("ring-border/40");
      expect(result).not.toContain("text-destructive");
      expect(result).not.toContain("text-success");
    });

    it("omits ring classes when excludeRing is true", () => {
      const result = statusVariants({ excludeRing: true, status: "active" });
      expect(result).not.toContain("ring-1");
      expect(result).not.toContain("ring-inset");
      expect(result).toContain("bg-success/10");
    });
  });

  describe("combined variants", () => {
    it("prefers status over urgency", () => {
      const result = statusVariants({ status: "pending", urgency: "high" });
      expect(result).toContain("bg-warning/10");
      expect(result).toContain("text-warning");
      expect(result).not.toContain("text-destructive");
    });

    it("prefers status over action", () => {
      const result = statusVariants({ action: "search", status: "error" });
      expect(result).toContain("bg-destructive/10");
      expect(result).toContain("text-destructive");
      expect(result).not.toContain("text-info");
    });

    it("uses action when status absent", () => {
      const result = statusVariants({ action: "deals" });
      expect(result).toContain("bg-warning/10");
      expect(result).toContain("text-warning");
    });
  });
});

describe("getToneColors", () => {
  it("returns correct colors for active tone", () => {
    const colors = getToneColors("active");
    expect(colors.text).toBe("text-success");
    expect(colors.bg).toBe("bg-success/10");
    expect(colors.border).toBe("border-success/20");
  });

  it("returns correct colors for error tone", () => {
    const colors = getToneColors("error");
    expect(colors.text).toBe("text-destructive");
    expect(colors.bg).toBe("bg-destructive/10");
    expect(colors.border).toBe("border-destructive/20");
  });

  it("returns correct colors for info tone", () => {
    const colors = getToneColors("info");
    expect(colors.text).toBe("text-info");
    expect(colors.bg).toBe("bg-info/10");
    expect(colors.border).toBe("border-info/20");
  });

  it("returns correct colors for pending tone", () => {
    const colors = getToneColors("pending");
    expect(colors.text).toBe("text-warning");
    expect(colors.bg).toBe("bg-warning/10");
    expect(colors.border).toBe("border-warning/20");
  });

  it("returns correct colors for unknown tone", () => {
    const colors = getToneColors("unknown");
    expect(colors.text).toBe("text-muted-foreground");
    expect(colors.bg).toBe("bg-muted");
    expect(colors.border).toBe("border-border");
  });

  it("falls back to unknown colors for invalid tone", () => {
    const colors = getToneColors(unsafeCast<never>("invalid"));
    expect(colors.text).toBe("text-muted-foreground");
    expect(colors.bg).toBe("bg-muted");
    expect(colors.border).toBe("border-border");
  });

  it("returns correct colors for action tones", () => {
    const dealColors = getToneColors("deals");
    expect(dealColors.text).toBe("text-warning");
    expect(dealColors.bg).toBe("bg-warning/10");
    expect(dealColors.border).toBe("border-warning/20");

    const exploreColors = getToneColors("explore");
    expect(exploreColors.text).toBe("text-highlight");
    expect(exploreColors.bg).toBe("bg-highlight/10");
    expect(exploreColors.border).toBe("border-highlight/20");
  });
});
