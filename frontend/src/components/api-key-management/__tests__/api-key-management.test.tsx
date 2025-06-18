import * as apiHooks from "@/hooks/use-api-keys";
import { useApiKeyStore } from "@/stores/api-key-store";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiKeyForm } from "../api-key-form";
import { ApiKeyInput } from "../api-key-input";
import { ApiKeyList } from "../api-key-list";
import { ApiKeySettings } from "../api-key-settings";
import { ServiceSelector } from "../service-selector";

// Mock the TanStack Query hooks
vi.mock("@/hooks/use-api-keys", () => ({
  useApiKeys: vi.fn(),
  useAddApiKey: vi.fn(),
  useDeleteApiKey: vi.fn(),
  useValidateApiKey: vi.fn(),
}));

// Mock Zustand store
vi.mock("@/stores/api-key-store", () => ({
  useApiKeyStore: vi.fn(),
}));

// Mock the toast component
vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe("API Key Management Components", () => {
  // Reset mocks before each test
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("ApiKeyInput Component", () => {
    it("renders correctly with default props", () => {
      renderWithProviders(<ApiKeyInput value="" onChange={() => {}} onBlur={() => {}} error="" />);

      expect(screen.getByPlaceholderText("Enter API key")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /toggle visibility/i })
      ).toBeInTheDocument();
    });

    it("toggles visibility when button is clicked", async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ApiKeyInput
          value="test-api-key"
          onChange={() => {}}
          onBlur={() => {}}
          error=""
        />
      );

      const input = screen.getByDisplayValue("test-api-key");
      expect(input).toHaveAttribute("type", "password");

      const toggleButton = screen.getByRole("button", {
        name: /show api key/i,
      });
      await user.click(toggleButton);

      expect(input).toHaveAttribute("type", "text");
    });

    it("displays error message when provided", () => {
      renderWithProviders(
        <ApiKeyInput
          value=""
          onChange={() => {}}
          onBlur={() => {}}
          error="API key is required"
        />
      );

      expect(screen.getByText("API key is required")).toBeInTheDocument();
    });
  });

  describe("ServiceSelector Component", () => {
    const mockServices = ["google-maps", "openai", "weather"];

    it("renders with provided services", () => {
      renderWithProviders(
        <ServiceSelector
          services={mockServices}
          selectedService=""
          onServiceChange={() => {}}
        />
      );

      expect(screen.getByPlaceholderText("Select a service")).toBeInTheDocument();
    });

    it("calls onChange when a service is selected", async () => {
      const mockOnChange = vi.fn();
      const user = userEvent.setup();

      renderWithProviders(
        <ServiceSelector
          services={mockServices}
          selectedService=""
          onServiceChange={mockOnChange}
        />
      );

      // Open dropdown
      const combobox = screen.getByRole("combobox");
      await user.click(combobox);

      // Select an option
      const option = screen.getByText("google-maps");
      await user.click(option);

      expect(mockOnChange).toHaveBeenCalledWith("google-maps");
    });
  });

  describe("ApiKeyForm Component", () => {
    beforeEach(() => {
      // Mock store
      vi.mocked(useApiKeyStore).mockReturnValue({
        supportedServices: ["google-maps", "openai"],
        selectedService: null,
        setSelectedService: vi.fn(),
      });

      // Mock API hooks
      vi.mocked(apiHooks.useValidateApiKey).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });

      vi.mocked(apiHooks.useAddApiKey).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });
    });

    it("renders the form correctly", () => {
      renderWithProviders(<ApiKeyForm />);

      expect(screen.getByText("Service")).toBeInTheDocument();
      expect(screen.getByText("API Key")).toBeInTheDocument();
      expect(screen.getByText("Save API Key", { exact: false })).toBeInTheDocument();
    });

    it("submits the form with valid data", async () => {
      const validateMock = vi.fn();
      vi.mocked(apiHooks.useValidateApiKey).mockReturnValue({
        mutate: validateMock,
        isPending: false,
      });

      const user = userEvent.setup();
      renderWithProviders(<ApiKeyForm />);

      // Fill in the form
      // Note: In a real test, we would properly simulate the service selection
      // For this simplified test, we're focusing on the API key input
      const apiKeyInput = screen.getByPlaceholderText("Enter API key");
      await user.type(apiKeyInput, "test-api-key-12345");

      // Submit the form
      const submitButton = screen.getByRole("button", {
        name: /validate & save/i,
      });
      await user.click(submitButton);

      // Verify validation was called
      expect(validateMock).toHaveBeenCalled();
    });
  });

  describe("ApiKeyList Component", () => {
    beforeEach(() => {
      vi.mocked(useApiKeyStore).mockReturnValue({
        keys: {
          "google-maps": {
            service: "google-maps",
            has_key: true,
            is_valid: true,
            last_validated: "2023-07-15T10:20:30Z",
            last_used: "2023-07-15T12:30:45Z",
          },
          openai: {
            service: "openai",
            has_key: true,
            is_valid: false,
            last_validated: "2023-07-14T10:20:30Z",
          },
        },
      });

      vi.mocked(apiHooks.useDeleteApiKey).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });

      vi.mocked(apiHooks.useValidateApiKey).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });
    });

    it("renders the list of API keys", () => {
      renderWithProviders(<ApiKeyList />);

      expect(screen.getByText("google-maps")).toBeInTheDocument();
      expect(screen.getByText("openai")).toBeInTheDocument();
      expect(screen.getAllByText("Validate").length).toBe(2);
      expect(screen.getAllByText("Remove").length).toBe(2);
    });

    it("calls delete function when remove is confirmed", async () => {
      const deleteMock = vi.fn();
      vi.mocked(apiHooks.useDeleteApiKey).mockReturnValue({
        mutate: deleteMock,
        isPending: false,
      });

      const user = userEvent.setup();
      renderWithProviders(<ApiKeyList />);

      // Click the first remove button
      const removeButtons = screen.getAllByText("Remove");
      await user.click(removeButtons[0]);

      // Confirm deletion
      const confirmButton = screen.getByText("Delete");
      await user.click(confirmButton);

      expect(deleteMock).toHaveBeenCalledWith({ service: "google-maps" });
    });
  });

  describe("ApiKeySettings Component", () => {
    beforeEach(() => {
      vi.mocked(apiHooks.useApiKeys).mockReturnValue({
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      });
    });

    it("renders tabs and content", () => {
      renderWithProviders(<ApiKeySettings />);

      expect(screen.getByText("Your API Keys")).toBeInTheDocument();
      expect(screen.getByText("Add New Key")).toBeInTheDocument();
    });

    it("shows loading state when loading", () => {
      vi.mocked(apiHooks.useApiKeys).mockReturnValue({
        isLoading: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<ApiKeySettings />);

      // Loading indicator should be visible
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("shows error state when error occurs", () => {
      vi.mocked(apiHooks.useApiKeys).mockReturnValue({
        isLoading: false,
        isError: true,
        error: new Error("Failed to load API keys"),
        refetch: vi.fn(),
      });

      renderWithProviders(<ApiKeySettings />);

      expect(screen.getByText("Error Loading API Keys")).toBeInTheDocument();
      expect(screen.getByText("Failed to load API keys")).toBeInTheDocument();
    });
  });
});
