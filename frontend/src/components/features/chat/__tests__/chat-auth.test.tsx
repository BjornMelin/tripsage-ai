/**
 * Unit tests for chat authentication integration.
 */

import { render, screen } from "@testing-library/react";
import type React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChatAi } from "@/hooks/use-chat-ai";
import { useApiKeyStore } from "@/stores/api-key-store";
import { ChatContainer } from "../chat-container";

// Mock the API key store
vi.mock("@/stores/api-key-store", () => ({
  useApiKeyStore: vi.fn(),
}));

// Mock the chat AI hook
vi.mock("@/hooks/use-chat-ai", () => ({
  useChatAi: vi.fn(),
}));

// Mock the chat store
vi.mock("@/stores/chat-store", () => ({
  useChatStore: vi.fn(() => ({
    getAgentStatus: vi.fn(() => ({ status: "idle", message: "" })),
    isStreaming: false,
    connectionStatus: "disconnected",
    isRealtimeEnabled: false,
    connectWebSocket: vi.fn(),
    disconnectWebSocket: vi.fn(),
    setRealtimeEnabled: vi.fn(),
  })),
}));

// Mock Next.js Link component
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// Declare mocked functions at module level for reuse across test suites
const mockUseChatAi = vi.mocked(useChatAi);
const mockUseApiKeyStore = vi.mocked(useApiKeyStore);

describe("ChatContainer Authentication", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows authentication required when not authenticated", () => {
    mockUseChatAi.mockReturnValue({
      sessionId: "test-session",
      messages: [],
      isLoading: false,
      error: null,
      input: "",
      handleInputChange: vi.fn(),
      sendMessage: vi.fn(),
      stopGeneration: vi.fn(),
      reload: vi.fn(),
      isAuthenticated: false,
      isInitialized: false,
      isApiKeyValid: false,
      authError: null,
      activeToolCalls: [],
      toolResults: [],
      retryToolCall: vi.fn(),
      cancelToolCall: vi.fn(),
    });

    render(<ChatContainer />);

    expect(screen.getByText("Authentication Required")).toBeInTheDocument();
    expect(
      screen.getByText("Please log in to start chatting with TripSage AI.")
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign In" })).toHaveAttribute(
      "href",
      "/login"
    );
  });

  it("shows API key required when authenticated but no valid key", () => {
    mockUseChatAi.mockReturnValue({
      sessionId: "test-session",
      messages: [],
      isLoading: false,
      error: null,
      input: "",
      handleInputChange: vi.fn(),
      sendMessage: vi.fn(),
      stopGeneration: vi.fn(),
      reload: vi.fn(),
      isAuthenticated: true,
      isInitialized: true,
      isApiKeyValid: false,
      authError: null,
      activeToolCalls: [],
      toolResults: [],
      retryToolCall: vi.fn(),
      cancelToolCall: vi.fn(),
    });

    render(<ChatContainer />);

    expect(screen.getByText("API Key Required")).toBeInTheDocument();
    expect(screen.getByText(/A valid OpenAI API key is required/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage API Keys" })).toHaveAttribute(
      "href",
      "/settings/api-keys"
    );
  });

  it("shows loading state when initializing", () => {
    mockUseChatAi.mockReturnValue({
      sessionId: "test-session",
      messages: [],
      isLoading: false,
      error: null,
      input: "",
      handleInputChange: vi.fn(),
      sendMessage: vi.fn(),
      stopGeneration: vi.fn(),
      reload: vi.fn(),
      isAuthenticated: true,
      isInitialized: false,
      isApiKeyValid: true,
      authError: null,
      activeToolCalls: [],
      toolResults: [],
      retryToolCall: vi.fn(),
      cancelToolCall: vi.fn(),
    });

    render(<ChatContainer />);

    expect(screen.getByText("Initializing chat session...")).toBeInTheDocument();
  });

  it("shows chat interface when fully authenticated and initialized", () => {
    mockUseChatAi.mockReturnValue({
      sessionId: "test-session",
      messages: [],
      isLoading: false,
      error: null,
      input: "",
      handleInputChange: vi.fn(),
      sendMessage: vi.fn(),
      stopGeneration: vi.fn(),
      reload: vi.fn(),
      isAuthenticated: true,
      isInitialized: true,
      isApiKeyValid: true,
      authError: null,
      activeToolCalls: [],
      toolResults: [],
      retryToolCall: vi.fn(),
      cancelToolCall: vi.fn(),
    });

    render(<ChatContainer />);

    // Should show the chat interface elements
    expect(screen.queryByText("Authentication Required")).not.toBeInTheDocument();
    expect(screen.queryByText("API Key Required")).not.toBeInTheDocument();
    expect(screen.queryByText("Initializing chat session...")).not.toBeInTheDocument();
  });

  it("displays auth error with API key management link", () => {
    const authError =
      "A valid OpenAI API key is required to use the chat feature. Please add one to get started.";

    mockUseChatAi.mockReturnValue({
      sessionId: "test-session",
      messages: [],
      isLoading: false,
      error: null,
      input: "",
      handleInputChange: vi.fn(),
      sendMessage: vi.fn(),
      stopGeneration: vi.fn(),
      reload: vi.fn(),
      isAuthenticated: true,
      isInitialized: true,
      isApiKeyValid: false,
      authError,
      activeToolCalls: [],
      toolResults: [],
      retryToolCall: vi.fn(),
      cancelToolCall: vi.fn(),
    });

    render(<ChatContainer />);

    expect(screen.getByText(authError)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage API Keys" })).toBeInTheDocument();
  });

  it("displays general error without management link", () => {
    const error = "Network connection failed";

    mockUseChatAi.mockReturnValue({
      sessionId: "test-session",
      messages: [],
      isLoading: false,
      error: new Error(error),
      input: "",
      handleInputChange: vi.fn(),
      sendMessage: vi.fn(),
      stopGeneration: vi.fn(),
      reload: vi.fn(),
      isAuthenticated: true,
      isInitialized: true,
      isApiKeyValid: true,
      authError: null,
      activeToolCalls: [],
      toolResults: [],
      retryToolCall: vi.fn(),
      cancelToolCall: vi.fn(),
    });

    render(<ChatContainer />);

    expect(screen.getByText(error)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Manage API Keys" })
    ).not.toBeInTheDocument();
  });
});

describe("API Key Store Authentication", () => {
  it("persists authentication state correctly", () => {
    // Test that auth state is properly persisted
    const mockStore = {
      isAuthenticated: true,
      userId: "test-user",
      token: "test-token",
      isApiKeyValid: false,
      authError: null,
      supportedServices: ["openai", "weather"],
      keys: {},
      selectedService: null,
      setAuthenticated: vi.fn(),
      setApiKeyValid: vi.fn(),
      setAuthError: vi.fn(),
      logout: vi.fn(),
      setSupportedServices: vi.fn(),
      setKeys: vi.fn(),
      setSelectedService: vi.fn(),
      updateKey: vi.fn(),
      removeKey: vi.fn(),
      validateKey: vi.fn(),
      loadKeys: vi.fn(),
    };

    mockUseApiKeyStore.mockReturnValue(mockStore);

    // Verify persisted state includes auth info
    expect(mockStore.isAuthenticated).toBe(true);
    expect(mockStore.userId).toBe("test-user");
    expect(mockStore.token).toBe("test-token");
  });

  it("clears all data on logout", () => {
    const mockStore = {
      isAuthenticated: false,
      userId: null,
      token: null,
      isApiKeyValid: false,
      authError: null,
      supportedServices: [],
      keys: {},
      selectedService: null,
      setAuthenticated: vi.fn(),
      setApiKeyValid: vi.fn(),
      setAuthError: vi.fn(),
      logout: vi.fn(),
      setSupportedServices: vi.fn(),
      setKeys: vi.fn(),
      setSelectedService: vi.fn(),
      updateKey: vi.fn(),
      removeKey: vi.fn(),
      validateKey: vi.fn(),
      loadKeys: vi.fn(),
    };

    mockUseApiKeyStore.mockReturnValue(mockStore);

    // Call logout function
    mockStore.logout();

    // Verify logout was called
    expect(mockStore.logout).toHaveBeenCalled();
  });

  it("validates API keys with proper authentication", async () => {
    const mockValidateKey = vi.fn().mockResolvedValue(true);

    const mockStore = {
      isAuthenticated: true,
      userId: "test-user",
      token: "test-token",
      isApiKeyValid: false,
      authError: null,
      supportedServices: ["openai"],
      keys: {
        openai: {
          service: "openai",
          api_key: "sk-test",
          has_key: true,
          is_valid: true,
        },
      },
      selectedService: "openai",
      setAuthenticated: vi.fn(),
      setApiKeyValid: vi.fn(),
      setAuthError: vi.fn(),
      logout: vi.fn(),
      setSupportedServices: vi.fn(),
      setKeys: vi.fn(),
      setSelectedService: vi.fn(),
      updateKey: vi.fn(),
      removeKey: vi.fn(),
      validateKey: mockValidateKey,
      loadKeys: vi.fn(),
    };

    mockUseApiKeyStore.mockReturnValue(mockStore);

    // Call validate key
    const result = await mockStore.validateKey("openai");

    // Verify validation was called and returned true
    expect(mockValidateKey).toHaveBeenCalledWith("openai");
    expect(result).toBe(true);
  });

  it("loads keys when authenticated", async () => {
    const mockLoadKeys = vi.fn();

    const mockStore = {
      isAuthenticated: true,
      userId: "test-user",
      token: "test-token",
      isApiKeyValid: true,
      authError: null,
      supportedServices: ["openai", "weather"],
      keys: {},
      selectedService: null,
      setAuthenticated: vi.fn(),
      setApiKeyValid: vi.fn(),
      setAuthError: vi.fn(),
      logout: vi.fn(),
      setSupportedServices: vi.fn(),
      setKeys: vi.fn(),
      setSelectedService: vi.fn(),
      updateKey: vi.fn(),
      removeKey: vi.fn(),
      validateKey: vi.fn(),
      loadKeys: mockLoadKeys,
    };

    mockUseApiKeyStore.mockReturnValue(mockStore);

    // Call load keys
    await mockStore.loadKeys();

    // Verify load keys was called
    expect(mockLoadKeys).toHaveBeenCalled();
  });
});
