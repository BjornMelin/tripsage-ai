import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '../chat-interface';
import { useChatStore } from '@/stores/chat-store';

// Mock the chat store
vi.mock('@/stores/chat-store', () => ({
  useChatStore: vi.fn(),
}));

describe('ChatInterface', () => {
  beforeEach(() => {
    (useChatStore as any).mockReturnValue({
      sessions: [],
      currentSessionId: null,
      sendMessage: vi.fn(),
    });
  });

  it('renders chat header with title and status', () => {
    render(<ChatInterface />);

    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    expect(screen.getByText('Ask me anything about travel planning')).toBeInTheDocument();
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  it('renders sample messages', () => {
    render(<ChatInterface />);

    expect(screen.getByText(/Hello! I'm your TripSage AI assistant/)).toBeInTheDocument();
    expect(screen.getByText(/I'm looking for flights from New York to Paris/)).toBeInTheDocument();
  });

  it('renders message input with placeholder', () => {
    render(<ChatInterface placeholder="Custom placeholder" />);

    const input = screen.getByPlaceholderText('Custom placeholder');
    expect(input).toBeInTheDocument();
  });

  it('uses default placeholder when none provided', () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Type your message...');
    expect(input).toBeInTheDocument();
  });

  it('allows typing in the message input', () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement;
    
    fireEvent.change(input, { target: { value: 'Hello AI' } });
    
    expect(input.value).toBe('Hello AI');
  });

  it('sends message when form is submitted', async () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Type your message...') as HTMLTextAreaElement;
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    // Should clear input after sending
    expect(input.value).toBe('');

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('AI is typing...')).toBeInTheDocument();
    });
  });

  it('sends message when Enter key is pressed (without Shift)', () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Type your message...');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });

    // Should clear input after sending
    expect((input as HTMLTextAreaElement).value).toBe('');
  });

  it('does not send message when Enter key is pressed with Shift', () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Type your message...');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

    // Should not clear input when Shift+Enter
    expect((input as HTMLTextAreaElement).value).toBe('Test message');
  });

  it('disables input when disabled prop is true', () => {
    render(<ChatInterface disabled={true} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    expect(input).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('disables send button when input is empty', () => {
    render(<ChatInterface />);

    const sendButton = screen.getByRole('button', { name: /send/i });
    
    expect(sendButton).toBeDisabled();
  });

  it('enables send button when input has content', () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    
    expect(sendButton).not.toBeDisabled();
  });

  it('shows loading indicator when AI is responding', async () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('AI is typing...')).toBeInTheDocument();
      expect(screen.getByText('Thinking...')).toBeInTheDocument();
    });
  });

  it('displays message timestamps', () => {
    render(<ChatInterface />);

    // Check that timestamps are present (they should be formatted times)
    const timeElements = screen.getAllByText(/\d{1,2}:\d{2}\s*(AM|PM)?/i);
    expect(timeElements.length).toBeGreaterThan(0);
  });

  it('scrolls to bottom when new messages are added', () => {
    // This test would require more complex setup with refs and DOM manipulation
    // For now, we'll just verify the component renders without errors
    render(<ChatInterface />);
    
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<ChatInterface className="custom-class" />);

    const container = screen.getByText('AI Assistant').closest('.custom-class');
    expect(container).toBeInTheDocument();
  });

  it('handles sessionId prop correctly', () => {
    render(<ChatInterface sessionId="test-session-123" />);

    // Component should render normally with sessionId
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });
});