/** @vitest-environment jsdom */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { FieldValues, UseFormProps } from "react-hook-form";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthCore } from "@/features/auth/store/auth/auth-core";
import { PersonalInfoSection } from "../personal-info-section";

vi.mock("@/features/auth/store/auth/auth-core");
vi.mock("@/lib/supabase", () => ({
  getBrowserClient: vi.fn(),
}));

// Mock useZodForm to use standard useForm to avoid async validation issues in tests
vi.mock("@/hooks/use-zod-form", async () => {
  const { useForm } = await import("react-hook-form");
  const { zodResolver } = await import("@hookform/resolvers/zod");
  type ZodResolverSchema = Parameters<typeof zodResolver>[0];
  return {
    useZodForm: ({
      schema,
      defaultValues,
      mode,
    }: {
      schema: ZodResolverSchema;
      defaultValues: FieldValues;
      mode?: UseFormProps<FieldValues>["mode"];
    }) => {
      return useForm({
        defaultValues,
        mode,
        resolver: zodResolver(schema),
      });
    },
  };
});

const TOAST_SPY = vi.fn();
vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: TOAST_SPY }),
}));

const MOCK_SET_USER = vi.fn();
const MOCK_UPDATE_USER = vi.fn();
const MOCK_REMOVE = vi.fn();
const MOCK_UPLOAD = vi.fn();
const MOCK_GET_PUBLIC_URL = vi.fn();

const GET_BROWSER_CLIENT = vi.mocked((await import("@/lib/supabase")).getBrowserClient);

function CreateDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

const BASE_USER = {
  avatarUrl: "https://example.com/avatars/user-1.jpg",
  bio: "Travel enthusiast",
  createdAt: "2025-01-01T00:00:00.000Z",
  displayName: "John Doe",
  email: "test@example.com",
  firstName: "John",
  id: "user-1",
  isEmailVerified: true,
  lastName: "Doe",
  location: "New York, USA",
  updatedAt: "2025-01-01T00:00:00.000Z",
  website: "https://johndoe.com",
};

describe("PersonalInfoSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    const bucket = {
      getPublicUrl: MOCK_GET_PUBLIC_URL,
      remove: MOCK_REMOVE,
      upload: MOCK_UPLOAD,
    };
    MOCK_REMOVE.mockResolvedValue({ data: null, error: null });
    MOCK_UPLOAD.mockResolvedValue({
      data: { path: "avatars/user-1.jpg" },
      error: null,
    });
    MOCK_GET_PUBLIC_URL.mockReturnValue({
      data: { publicUrl: "https://cdn.example.com/avatars/user-1.jpg" },
    });
    MOCK_UPDATE_USER.mockResolvedValue({
      data: { user: { updated_at: "2025-01-02T00:00:00.000Z" } },
      error: null,
    });

    GET_BROWSER_CLIENT.mockReturnValue({
      auth: { updateUser: MOCK_UPDATE_USER },
      storage: { from: () => bucket },
    } as never);

    vi.mocked(useAuthCore).mockReturnValue({
      setUser: MOCK_SET_USER,
      user: BASE_USER,
    } as never);
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

    await waitFor(() => expect(MOCK_UPDATE_USER).not.toHaveBeenCalled());
  });

  it("validates website URL format", async () => {
    render(<PersonalInfoSection />);

    const websiteInput = screen.getByLabelText(/website/i);
    fireEvent.change(websiteInput, { target: { value: "invalid-url" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(MOCK_UPDATE_USER).not.toHaveBeenCalled());
  });

  it("submits form successfully", async () => {
    render(<PersonalInfoSection />);

    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() =>
      expect(MOCK_UPDATE_USER).toHaveBeenCalledWith({
        data: {
          bio: "Travel enthusiast",
          display_name: "John Doe",
          first_name: "John",
          full_name: "John Doe",
          last_name: "Doe",
          location: "New York, USA",
          website: "https://johndoe.com",
        },
      })
    );

    expect(MOCK_SET_USER).toHaveBeenCalledWith(
      expect.objectContaining({
        bio: "Travel enthusiast",
        displayName: "John Doe",
        firstName: "John",
        lastName: "Doe",
        location: "New York, USA",
        website: "https://johndoe.com",
      })
    );
    expect(TOAST_SPY).toHaveBeenCalledWith({
      description: "Your personal information has been successfully updated.",
      title: "Profile updated",
    });
  });

  it("handles avatar upload validations", () => {
    const { container } = render(<PersonalInfoSection />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const invalidFile = new File(["content"], "test.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [invalidFile] } });
    expect(TOAST_SPY).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Invalid file type" })
    );

    const largeFile = new File(["x".repeat(6 * 1024 * 1024)], "large.jpg", {
      type: "image/jpeg",
    });
    fireEvent.change(fileInput, { target: { files: [largeFile] } });
    expect(TOAST_SPY).toHaveBeenCalledWith(
      expect.objectContaining({ title: "File too large" })
    );
  });

  it("labels avatar upload trigger and announces upload progress", async () => {
    const upload = CreateDeferred<{ data: { path: string }; error: null }>();
    MOCK_UPLOAD.mockReturnValueOnce(upload.promise);

    const { container } = render(<PersonalInfoSection />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const trigger = screen.getByRole("button", { name: "Upload profile picture" });

    expect(trigger).toHaveAttribute("aria-controls", fileInput.id);
    expect(trigger).toHaveAccessibleDescription(/recommended size: 400x400px/i);

    const validFile = new File(["content"], "avatar.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    const busyTrigger = await screen.findByRole("button", {
      name: "Uploading profile picture",
    });
    expect(busyTrigger).toBeDisabled();
    expect(busyTrigger).toHaveAttribute("aria-busy", "true");

    upload.resolve({
      data: { path: "avatars/user-1.jpg" },
      error: null,
    });
    await waitFor(() => expect(MOCK_UPDATE_USER).toHaveBeenCalled());
  });

  it("uploads avatar and shows success toast", async () => {
    const { container } = render(<PersonalInfoSection />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const validFile = new File(["content"], "avatar.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => expect(MOCK_UPLOAD).toHaveBeenCalled());
    expect(MOCK_UPLOAD).toHaveBeenCalledWith("user-1.jpg", validFile, {
      cacheControl: "public, max-age=3600",
      contentType: "image/jpeg",
      upsert: true,
    });
    // Avatar URL includes cache-busting query parameter
    expect(MOCK_UPDATE_USER).toHaveBeenCalledWith({
      data: {
        avatar_url: expect.stringMatching(
          /^https:\/\/cdn\.example\.com\/avatars\/user-1\.jpg\?v=[a-z0-9]{1,8}$/
        ),
      },
    });
    expect(TOAST_SPY).toHaveBeenCalledWith({
      description: "Your profile picture has been successfully updated.",
      title: "Avatar updated",
    });
  });
});
