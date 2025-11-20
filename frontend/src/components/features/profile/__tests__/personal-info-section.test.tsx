/** @vitest-environment jsdom */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useUserProfileStore } from "@/stores/user-store";
import { PersonalInfoSection } from "../personal-info-section";

vi.mock("@/stores/user-store");

const toastSpy = vi.fn();
vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: toastSpy }),
}));

const mockUploadAvatar = vi.fn();
const mockUpdatePersonalInfo = vi.fn();

const baseProfile = {
  avatarUrl: "https://example.com/avatar.jpg",
  email: "test@example.com",
  personalInfo: {
    bio: "Travel enthusiast",
    displayName: "John Doe",
    firstName: "John",
    lastName: "Doe",
    location: "New York, USA",
    website: "https://johndoe.com",
  },
};

describe("PersonalInfoSection", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    mockUploadAvatar.mockResolvedValue("https://cdn.example.com/new-avatar.jpg");
    mockUpdatePersonalInfo.mockResolvedValue(true);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: baseProfile,
      updatePersonalInfo: mockUpdatePersonalInfo,
      uploadAvatar: mockUploadAvatar,
    });
  });

  it("renders personal information form with profile defaults", () => {
    render(<PersonalInfoSection />);

    expect(screen.getByDisplayValue("John")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Doe")).toBeInTheDocument();
    expect(screen.getByDisplayValue("John Doe")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Travel enthusiast")).toBeInTheDocument();
    expect(screen.getByDisplayValue("New York, USA")).toBeInTheDocument();
    expect(screen.getByDisplayValue("https://johndoe.com")).toBeInTheDocument();
  });

  it("validates required first name", async () => {
    render(<PersonalInfoSection />);

    const firstNameInput = screen.getByLabelText(/first name/i);
    fireEvent.change(firstNameInput, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await vi.runAllTimersAsync();
    await Promise.resolve();
    expect(mockUpdatePersonalInfo).not.toHaveBeenCalled();
  });

  it("validates website URL format", async () => {
    render(<PersonalInfoSection />);

    const websiteInput = screen.getByLabelText(/website/i);
    fireEvent.change(websiteInput, { target: { value: "invalid-url" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await vi.runAllTimersAsync();
    await Promise.resolve();
    expect(mockUpdatePersonalInfo).not.toHaveBeenCalled();
  });

  it("submits form successfully", async () => {
    render(<PersonalInfoSection />);

    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await vi.runAllTimersAsync();
    await Promise.resolve();

    expect(mockUpdatePersonalInfo).toHaveBeenCalledWith({
      bio: "Travel enthusiast",
      displayName: "John Doe",
      firstName: "John",
      lastName: "Doe",
      location: "New York, USA",
      website: "https://johndoe.com",
    });
    expect(toastSpy).toHaveBeenCalledWith({
      description: "Your personal information has been successfully updated.",
      title: "Profile updated",
    });
  });

  it("handles avatar upload validations", async () => {
    const { container } = render(<PersonalInfoSection />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const invalidFile = new File(["content"], "test.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [invalidFile] } });
    expect(toastSpy).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Invalid file type" })
    );

    const largeFile = new File(["x".repeat(6 * 1024 * 1024)], "large.jpg", {
      type: "image/jpeg",
    });
    fireEvent.change(fileInput, { target: { files: [largeFile] } });
    expect(toastSpy).toHaveBeenCalledWith(
      expect.objectContaining({ title: "File too large" })
    );
  });

  it("uploads avatar and shows success toast", async () => {
    const { container } = render(<PersonalInfoSection />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const validFile = new File(["content"], "avatar.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await Promise.resolve();

    expect(mockUploadAvatar).toHaveBeenCalledWith(validFile);
    expect(toastSpy).toHaveBeenCalledWith({
      description: "Your profile picture has been successfully updated.",
      title: "Avatar updated",
    });
  });
});
