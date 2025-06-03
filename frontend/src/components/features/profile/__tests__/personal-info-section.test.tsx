import { useUserStore } from "@/stores/user-store";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { PersonalInfoSection } from "../personal-info-section";

// Mock the stores and hooks
vi.mock("@/stores/user-store");
vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const mockUser = {
  id: "1",
  email: "test@example.com",
  firstName: "John",
  lastName: "Doe",
  displayName: "John Doe",
  bio: "Travel enthusiast",
  location: "New York, USA",
  website: "https://johndoe.com",
  avatarUrl: "https://example.com/avatar.jpg",
  isEmailVerified: true,
};

const mockUpdateUser = vi.fn();

describe("PersonalInfoSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useUserStore as any).mockReturnValue({
      user: mockUser,
      updateUser: mockUpdateUser,
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
    (useUserStore as any).mockReturnValue({
      user: { ...mockUser, avatarUrl: undefined },
      updateUser: mockUpdateUser,
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
      expect(mockUpdateUser).toHaveBeenCalledWith({
        firstName: "John",
        lastName: "Doe",
        displayName: "John Doe",
        bio: "Travel enthusiast",
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
      expect(mockToast).toHaveBeenCalledWith({
        title: "Invalid file type",
        description: "Please select an image file.",
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
      expect(mockToast).toHaveBeenCalledWith({
        title: "File too large",
        description: "Please select an image smaller than 5MB.",
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
      expect(mockUpdateUser).toHaveBeenCalledWith({
        avatarUrl: "mocked-url",
      });
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Avatar updated",
        description: "Your profile picture has been successfully updated.",
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
      { user: { firstName: "John", lastName: "Doe" }, expected: "JD" },
      { user: { displayName: "Jane Smith" }, expected: "JS" },
      { user: { displayName: "Alice" }, expected: "AL" },
      { user: { email: "test@example.com" }, expected: "TE" },
    ];

    testCases.forEach(({ user, expected }) => {
      (useUserStore as any).mockReturnValue({
        user: { ...mockUser, ...user },
        updateUser: mockUpdateUser,
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
    mockUpdateUser.mockRejectedValueOnce(new Error("Network error"));

    render(<PersonalInfoSection />);

    const submitButton = screen.getByRole("button", { name: /save changes/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to update profile. Please try again.",
        variant: "destructive",
      });
    });
  });
});
