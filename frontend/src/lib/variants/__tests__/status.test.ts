import { describe, expect, it } from "vitest";
import { statusVariants } from "../status";

describe("statusVariants", () => {
  describe("urgency variants", () => {
    it("returns high urgency classes", () => {
      const result = statusVariants({ urgency: "high" });
      expect(result).toContain("bg-red-50");
      expect(result).toContain("text-red-700");
      expect(result).toContain("ring-red-600/20");
    });

    it("returns medium urgency classes", () => {
      const result = statusVariants({ urgency: "medium" });
      expect(result).toContain("bg-amber-50");
      expect(result).toContain("text-amber-700");
      expect(result).toContain("ring-amber-600/20");
    });

    it("returns low urgency classes", () => {
      const result = statusVariants({ urgency: "low" });
      expect(result).toContain("bg-green-50");
      expect(result).toContain("text-green-700");
      expect(result).toContain("ring-green-600/20");
    });
  });

  describe("status variants", () => {
    it("returns active status classes", () => {
      const result = statusVariants({ status: "active" });
      expect(result).toContain("bg-green-50");
      expect(result).toContain("text-green-700");
      expect(result).toContain("ring-green-600/20");
    });

    it("returns error status classes", () => {
      const result = statusVariants({ status: "error" });
      expect(result).toContain("bg-red-50");
      expect(result).toContain("text-red-700");
      expect(result).toContain("ring-red-600/20");
    });

    it("returns pending status classes", () => {
      const result = statusVariants({ status: "pending" });
      expect(result).toContain("bg-amber-50");
      expect(result).toContain("text-amber-700");
      expect(result).toContain("ring-amber-600/20");
    });

    it("returns info status classes", () => {
      const result = statusVariants({ status: "info" });
      expect(result).toContain("bg-blue-50");
      expect(result).toContain("text-blue-700");
      expect(result).toContain("ring-blue-600/20");
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
      const result = statusVariants({ tone: "invalid" as unknown as never });
      expect(result).toContain("bg-slate-50");
      expect(result).toContain("text-slate-700");
      expect(result).toContain("ring-slate-600/20");
      expect(result).not.toContain("text-red-700");
      expect(result).not.toContain("text-green-700");
    });

    it("omits ring classes when excludeRing is true", () => {
      const result = statusVariants({ excludeRing: true, status: "active" });
      expect(result).not.toContain("ring-1");
      expect(result).not.toContain("ring-inset");
      expect(result).toContain("bg-green-50");
    });
  });

  describe("combined variants", () => {
    it("prefers status over urgency", () => {
      const result = statusVariants({ status: "pending", urgency: "high" });
      expect(result).toContain("bg-amber-50");
      expect(result).toContain("text-amber-700");
      expect(result).not.toContain("text-red-700");
    });

    it("prefers status over action", () => {
      const result = statusVariants({ action: "search", status: "error" });
      expect(result).toContain("bg-red-50");
      expect(result).toContain("text-red-700");
      expect(result).not.toContain("text-blue-700");
    });

    it("uses action when status absent", () => {
      const result = statusVariants({ action: "deals" });
      expect(result).toContain("bg-orange-50");
      expect(result).toContain("text-orange-700");
    });
  });
});
