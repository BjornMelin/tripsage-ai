import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApiKeyForm } from '../api-key-form';
import { ApiKeyList } from '../api-key-list';
import { ApiKeySettings } from '../api-key-settings';
import { ApiKeyInput } from '../api-key-input';
import { ServiceSelector } from '../service-selector';
import * as apiHooks from '@/lib/hooks/use-api-keys';
import { useApiKeyStore } from '@/stores/api-key-store';

// Mock the TanStack Query hooks
vi.mock('@/lib/hooks/use-api-keys', () => ({
  useApiKeys: vi.fn(),
  useAddApiKey: vi.fn(),
  useDeleteApiKey: vi.fn(),
  useValidateApiKey: vi.fn(),
}));

// Mock Zustand store
vi.mock('@/stores/api-key-store', () => ({
  useApiKeyStore: vi.fn(),
}));

// Mock the toast component
vi.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe('API Key Management Components', () => {
  // Reset mocks before each test
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('ApiKeyInput Component', () => {
    it('renders correctly with default props', () => {
      render(
        <ApiKeyInput
          value=""
          onChange={() => {}}
          onBlur={() => {}}
          isVisible={false}
          onVisibilityToggle={() => {}}
          error=""
        />
      );
      
      expect(screen.getByPlaceholderText('Enter API key')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /toggle visibility/i })).toBeInTheDocument();
    });

    it('toggles visibility when button is clicked', async () => {
      const mockToggle = vi.fn();
      const user = userEvent.setup();
      
      render(
        <ApiKeyInput
          value="test-api-key"
          onChange={() => {}}
          onBlur={() => {}}
          isVisible={false}
          onVisibilityToggle={mockToggle}
          error=""
        />
      );
      
      const toggleButton = screen.getByRole('button', { name: /toggle visibility/i });
      await user.click(toggleButton);
      
      expect(mockToggle).toHaveBeenCalledTimes(1);
    });

    it('displays error message when provided', () => {
      render(
        <ApiKeyInput
          value=""
          onChange={() => {}}
          onBlur={() => {}}
          isVisible={false}
          onVisibilityToggle={() => {}}
          error="API key is required"
        />
      );
      
      expect(screen.getByText('API key is required')).toBeInTheDocument();
    });
  });

  describe('ServiceSelector Component', () => {
    const mockServices = ['google-maps', 'openai', 'weather'];
    
    it('renders with provided services', () => {
      render(
        <ServiceSelector
          services={mockServices}
          selectedService=""
          onServiceChange={() => {}}
        />
      );
      
      expect(screen.getByPlaceholderText('Select a service')).toBeInTheDocument();
    });

    it('calls onChange when a service is selected', async () => {
      const mockOnChange = vi.fn();
      const user = userEvent.setup();
      
      render(
        <ServiceSelector
          services={mockServices}
          selectedService=""
          onServiceChange={mockOnChange}
        />
      );
      
      // Open dropdown
      const combobox = screen.getByRole('combobox');
      await user.click(combobox);
      
      // Select an option
      const option = screen.getByText('google-maps');
      await user.click(option);
      
      expect(mockOnChange).toHaveBeenCalledWith('google-maps');
    });
  });

  describe('ApiKeyForm Component', () => {
    beforeEach(() => {
      // Mock store
      (useApiKeyStore as any).mockReturnValue({
        supportedServices: ['google-maps', 'openai'],
        selectedService: null,
        setSelectedService: vi.fn(),
      });
      
      // Mock API hooks
      (apiHooks.useValidateApiKey as any).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });
      
      (apiHooks.useAddApiKey as any).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });
    });

    it('renders the form correctly', () => {
      render(<ApiKeyForm />);
      
      expect(screen.getByText('Service')).toBeInTheDocument();
      expect(screen.getByText('API Key')).toBeInTheDocument();
      expect(screen.getByText('Save API Key', { exact: false })).toBeInTheDocument();
    });

    it('submits the form with valid data', async () => {
      const validateMock = vi.fn();
      (apiHooks.useValidateApiKey as any).mockReturnValue({
        mutate: validateMock,
        isPending: false,
      });
      
      const user = userEvent.setup();
      render(<ApiKeyForm />);
      
      // Fill in the form
      // Note: In a real test, we would properly simulate the service selection
      // For this simplified test, we're focusing on the API key input
      const apiKeyInput = screen.getByPlaceholderText('Enter API key');
      await user.type(apiKeyInput, 'test-api-key-12345');
      
      // Submit the form
      const submitButton = screen.getByRole('button', { name: /validate & save/i });
      await user.click(submitButton);
      
      // Verify validation was called
      expect(validateMock).toHaveBeenCalled();
    });
  });

  describe('ApiKeyList Component', () => {
    beforeEach(() => {
      (useApiKeyStore as any).mockReturnValue({
        keys: {
          'google-maps': {
            service: 'google-maps',
            has_key: true,
            is_valid: true,
            last_validated: '2023-07-15T10:20:30Z',
            last_used: '2023-07-15T12:30:45Z',
          },
          'openai': {
            service: 'openai',
            has_key: true,
            is_valid: false,
            last_validated: '2023-07-14T10:20:30Z',
          },
        },
      });
      
      (apiHooks.useDeleteApiKey as any).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });
      
      (apiHooks.useValidateApiKey as any).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      });
    });

    it('renders the list of API keys', () => {
      render(<ApiKeyList />);
      
      expect(screen.getByText('google-maps')).toBeInTheDocument();
      expect(screen.getByText('openai')).toBeInTheDocument();
      expect(screen.getAllByText('Validate').length).toBe(2);
      expect(screen.getAllByText('Remove').length).toBe(2);
    });

    it('calls delete function when remove is confirmed', async () => {
      const deleteMock = vi.fn();
      (apiHooks.useDeleteApiKey as any).mockReturnValue({
        mutate: deleteMock,
        isPending: false,
      });
      
      const user = userEvent.setup();
      render(<ApiKeyList />);
      
      // Click the first remove button
      const removeButtons = screen.getAllByText('Remove');
      await user.click(removeButtons[0]);
      
      // Confirm deletion
      const confirmButton = screen.getByText('Delete');
      await user.click(confirmButton);
      
      expect(deleteMock).toHaveBeenCalledWith({ service: 'google-maps' });
    });
  });

  describe('ApiKeySettings Component', () => {
    beforeEach(() => {
      (apiHooks.useApiKeys as any).mockReturnValue({
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      });
    });

    it('renders tabs and content', () => {
      render(<ApiKeySettings />);
      
      expect(screen.getByText('Your API Keys')).toBeInTheDocument();
      expect(screen.getByText('Add New Key')).toBeInTheDocument();
    });

    it('shows loading state when loading', () => {
      (apiHooks.useApiKeys as any).mockReturnValue({
        isLoading: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      });
      
      render(<ApiKeySettings />);
      
      // Loading indicator should be visible
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('shows error state when error occurs', () => {
      (apiHooks.useApiKeys as any).mockReturnValue({
        isLoading: false,
        isError: true,
        error: new Error('Failed to load API keys'),
        refetch: vi.fn(),
      });
      
      render(<ApiKeySettings />);
      
      expect(screen.getByText('Error Loading API Keys')).toBeInTheDocument();
      expect(screen.getByText('Failed to load API keys')).toBeInTheDocument();
    });
  });
});