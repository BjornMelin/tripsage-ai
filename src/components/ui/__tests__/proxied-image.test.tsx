/** @vitest-environment jsdom */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProxiedImage } from "@/components/ui/proxied-image";
import { render, screen } from "@/test/test-utils";

const { mockRecordClientErrorOnActiveSpan } = vi.hoisted(() => ({
  mockRecordClientErrorOnActiveSpan: vi.fn(),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
}));

describe("ProxiedImage", () => {
  beforeEach(() => {
    mockRecordClientErrorOnActiveSpan.mockReset();
  });

  it("renders proxied remote images when dimensions are provided", () => {
    render(
      <ProxiedImage
        src="https://images.example.com/photo.jpg"
        alt="Mountain hotel"
        width={640}
        height={360}
      />
    );

    expect(screen.getByRole("img", { name: "Mountain hotel" })).toHaveAttribute(
      "src",
      "/api/images/proxy?url=https%3A%2F%2Fimages.example.com%2Fphoto.jpg"
    );
    expect(mockRecordClientErrorOnActiveSpan).not.toHaveBeenCalled();
  });

  it("reports missing dimensions through telemetry and renders fallback content", () => {
    render(
      <ProxiedImage
        src="/hotel.jpg"
        alt="Hotel"
        width={640}
        fallback={<span>Image unavailable</span>}
      />
    );

    expect(screen.getByText("Image unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Hotel" })).not.toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(expect.any(Error), {
      action: "validateDimensions",
      context: "ProxiedImage",
      hasHeight: false,
      hasWidth: true,
    });
  });

  it("keeps fallback rendering when telemetry recording fails", () => {
    mockRecordClientErrorOnActiveSpan.mockImplementationOnce(() => {
      throw new Error("telemetry unavailable");
    });

    render(<ProxiedImage src="/hotel.jpg" alt="Hotel" />);

    expect(screen.getByText("No image")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Hotel" })).not.toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(expect.any(Error), {
      action: "validateDimensions",
      context: "ProxiedImage",
      hasHeight: false,
      hasWidth: false,
    });
  });

  it("allows fill images without explicit dimensions", () => {
    render(
      <div className="relative h-40 w-40">
        <ProxiedImage src="/hotel.jpg" alt="Hotel" fill />
      </div>
    );

    expect(screen.getByRole("img", { name: "Hotel" })).toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).not.toHaveBeenCalled();
  });
});
