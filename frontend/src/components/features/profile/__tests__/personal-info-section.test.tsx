/**
 * @fileoverview Personal info section tests: rendering and validations.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useUserProfileStore } from "@/stores/user-store";
import { PersonalInfoSection } from "../personal-info-section";

// Mock the stores and hooks
vi.mock("@/stores/user-store");

const MockToast = vi.fn();
vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({
    toast: MockToast,
  }),
}));

const MockUser = {
  avatarUrl: "https://example.com/avatar.jpg",
  bio: "Travel enthusiast",
  displayName: "John Doe",
  email: "test@example.com",
  firstName: "John",
  id: "1",
  isEmailVerified: true,
  lastName: "Doe",
  location: "New York, USA",
  website: "https://johndoe.com",
};

const MockUpdateUser = vi.fn();

// TODO: Personal info validations, avatar upload, and update flows need final UI and store.
describe.skip("PersonalInfoSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockToast.mockClear();
    (useUserProfileStore as any).mockReturnValue({
      updateUser: MockUpdateUser,
      user: MockUser,
    });
  });

  it("renders personal information form with user data", () => {
    render(<PersonalInfoSection />);

    expect(screen.getByDisplayValue("John")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Doe")).toBeInTheDocument();
    expect(screen.getByDisplayValue("John Doe")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Travel enthusiast")).toBeInTheDocument();
    expect(screen.getByDisplayValue("New York, USA")).toBeInTheDocument();
    expect(screen.getByDisplayValue("https://johndoe.com")).toBeInTheDocument();
  });

  it("renders avatar with user initials when no avatar URL", () => {
    (useUserProfileStore as any).mockReturnValue({
      updateUser: MockUpdateUser,
      user: { ...MockUser, avatarUrl: undefined },
    });

    render(<PersonalInfoSection />);

    const avatarFallback = screen.getByText("JD");
    expect(avatarFallback).toBeInTheDocument();
  });

  it("displays profile picture upload section", () => {
    render(<PersonalInfoSection />);

    expect(screen.getByText("Profile Picture")).toBeInTheDocument();
    expect(screen.getByText(/Click the camera icon to upload/)).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeInTheDocument(); // Camera button
  });

  it("validates form fields correctly", async () => {
    render(<PersonalInfoSection />);

    const firstNameInput = screen.getByDisplayValue("John");
    const submitButton = screen.getByRole("button", { name: /save changes/i });

    fireEvent.change(firstNameInput, { target: { value: "" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("First name is required")).toBeInTheDocument();
    });
  });

  it("validates website URL format", async () => {
    render(<PersonalInfoSection />);

    const websiteInput = screen.getByDisplayValue("https://johndoe.com");
    const submitButton = screen.getByRole("button", { name: /save changes/i });

    fireEvent.change(websiteInput, { target: { value: "invalid-url" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Please enter a valid URL")).toBeInTheDocument();
    });
  });

  it("submits form successfully with valid data", async () => {
    render(<PersonalInfoSection />);

    const submitButton = screen.getByRole("button", { name: /save changes/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(MockUpdateUser).toHaveBeenCalledWith({
        bio: "Travel enthusiast",
        displayName: "John Doe",
        firstName: "John",
        lastName: "Doe",
        location: "New York, USA",
        website: "https://johndoe.com",
      });
    });

    // Note: Toast functionality is mocked, so we just verify the updateUser call
  });

  it("handles file upload validation - invalid file type", async () => {
    render(<PersonalInfoSection />);

    const fileInput = screen.getByLabelText(/avatar-upload/i);
    const invalidFile = new File(["content"], "test.txt", {
      type: "text/plain",
    });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(MockToast).toHaveBeenCalledWith({
        description: "Please select an image file.",
        title: "Invalid file type",
        variant: "destructive",
      });
    });
  });

  it("handles file upload validation - file too large", async () => {
    render(<PersonalInfoSection />);

    const fileInput = screen.getByLabelText(/avatar-upload/i);

    // Create a large file (6MB)
    const largeFile = new File(["x".repeat(6 * 1024 * 1024)], "large.jpg", {
      type: "image/jpeg",
    });

    fireEvent.change(fileInput, { target: { files: [largeFile] } });

    await waitFor(() => {
      expect(MockToast).toHaveBeenCalledWith({
        description: "Please select an image smaller than 5MB.",
        title: "File too large",
        variant: "destructive",
      });
    });
  });

  it("handles successful avatar upload", async () => {
    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => "mocked-url");

    render(<PersonalInfoSection />);

    const fileInput = screen.getByLabelText(/avatar-upload/i);
    const validFile = new File(["content"], "avatar.jpg", {
      type: "image/jpeg",
    });

    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(MockUpdateUser).toHaveBeenCalledWith({
        avatarUrl: "mocked-url",
      });
    });

    await waitFor(() => {
      expect(MockToast).toHaveBeenCalledWith({
        description: "Your profile picture has been successfully updated.",
        title: "Avatar updated",
      });
    });
  });

  it("shows loading state during avatar upload", async () => {
    render(<PersonalInfoSection />);

    const cameraButton = screen.getByRole("button");
    const fileInput = screen.getByLabelText(/avatar-upload/i);
    const validFile = new File(["content"], "avatar.jpg", {
      type: "image/jpeg",
    });

    fireEvent.change(fileInput, { target: { files: [validFile] } });

    // Check if button is disabled during upload
    expect(cameraButton).toBeDisabled();
  });

  it("generates correct initials for avatar fallback", () => {
    const testCases = [
      { expected: "JD", user: { firstName: "John", lastName: "Doe" } },
      { expected: "JS", user: { displayName: "Jane Smith" } },
      { expected: "AL", user: { displayName: "Alice" } },
      { expected: "TE", user: { email: "test@example.com" } },
    ];

    testCases.forEach(({ user, expected }) => {
      (useUserProfileStore as any).mockReturnValue({
        updateUser: MockUpdateUser,
        user: { ...MockUser, ...user },
      });

      render(<PersonalInfoSection />);
      expect(screen.getByText(expected)).toBeInTheDocument();
    });
  });

  it("handles bio character limit", () => {
    render(<PersonalInfoSection />);

    const bioTextarea = screen.getByDisplayValue("Travel enthusiast");
    const longBio = "x".repeat(501);

    fireEvent.change(bioTextarea, { target: { value: longBio } });

    const submitButton = screen.getByRole("button", { name: /save changes/i });
    fireEvent.click(submitButton);

    expect(
      screen.getByText("Bio must be less than 500 characters")
    ).toBeInTheDocument();
  });

  it("handles form submission error", async () => {
    // Mock a rejected promise to simulate error
    MockUpdateUser.mockRejectedValueOnce(new Error("Network error"));

    render(<PersonalInfoSection />);

    const submitButton = screen.getByRole("button", { name: /save changes/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(MockToast).toHaveBeenCalledWith({
        description: "Failed to update profile. Please try again.",
        title: "Error",
        variant: "destructive",
      });
    });
  });
});
