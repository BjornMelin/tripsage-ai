import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth, type User } from '../auth-context'
import { createClient } from '@/lib/supabase/client'
import type { User as SupabaseUser } from '@supabase/supabase-js'

// Mock Next.js router
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

// Mock Supabase client
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn()
}))

// Test component to consume auth context
function TestComponent() {
  const auth = useAuth()
  return (
    <div>
      <div data-testid="user">{auth.user?.email || 'No user'}</div>
      <div data-testid="user-name">{auth.user?.name || 'No name'}</div>
      <div data-testid="user-full-name">{auth.user?.full_name || 'No full name'}</div>
      <div data-testid="user-avatar">{auth.user?.avatar_url || 'No avatar'}</div>
      <div data-testid="user-created">{auth.user?.created_at || 'No created date'}</div>
      <div data-testid="user-updated">{auth.user?.updated_at || 'No updated date'}</div>
      <div data-testid="authenticated">{auth.isAuthenticated.toString()}</div>
      <div data-testid="loading">{auth.isLoading.toString()}</div>
      <div data-testid="error">{auth.error || 'No error'}</div>
      <button onClick={() => auth.signIn('test@example.com', 'password')}>Sign In</button>
      <button onClick={() => auth.signUp('test@example.com', 'password', 'Test User')}>Sign Up</button>
      <button onClick={() => auth.signUp('test@example.com', 'password')}>Sign Up No Name</button>
      <button onClick={() => auth.signOut()}>Sign Out</button>
      <button onClick={() => auth.refreshUser()}>Refresh</button>
      <button onClick={() => auth.clearError()}>Clear Error</button>
    </div>
  )
}


describe('AuthContext', () => {
  let mockSupabase: any

  beforeEach(() => {
    vi.clearAllMocks()
    mockPush.mockClear()
    
    // Create mock Supabase client
    mockSupabase = {
      auth: {
        getUser: vi.fn(),
        signInWithPassword: vi.fn(),
        signUp: vi.fn(),
        signOut: vi.fn(),
        onAuthStateChange: vi.fn()
      }
    }
    
    vi.mocked(createClient).mockReturnValue(mockSupabase)
  })

  it('should render without authenticated user initially', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('No user')
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    expect(screen.getByTestId('error')).toHaveTextContent('No error')
  })

  it('should render with initial user prop', async () => {
    const initialUser: User = {
      id: 'user123',
      email: 'test@example.com',
      name: 'Test User',
      full_name: 'Test User',
      avatar_url: 'https://example.com/avatar.jpg',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    render(
      <AuthProvider initialUser={initialUser}>
        <TestComponent />
      </AuthProvider>
    )

    expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    expect(screen.getByTestId('user')).toHaveTextContent('test@example.com')
    expect(screen.getByTestId('user-name')).toHaveTextContent('Test User')
    expect(screen.getByTestId('user-full-name')).toHaveTextContent('Test User')
    expect(screen.getByTestId('user-avatar')).toHaveTextContent('https://example.com/avatar.jpg')
  })

  it('should render with authenticated user from session', async () => {
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: { 
        full_name: 'Test User',
        avatar_url: 'https://example.com/avatar.jpg'
      },
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { user: mockUser }, 
      error: null 
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('test@example.com')
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    expect(screen.getByTestId('user-name')).toHaveTextContent('Test User')
    expect(screen.getByTestId('user-full-name')).toHaveTextContent('Test User')
    expect(screen.getByTestId('user-avatar')).toHaveTextContent('https://example.com/avatar.jpg')
  })

  it('should handle user without full_name correctly', async () => {
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { user: mockUser }, 
      error: null 
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user-name')).toHaveTextContent('test')
    expect(screen.getByTestId('user-full-name')).toHaveTextContent('No full name')
  })

  it('should handle session error on initialization', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { session: null }, 
      error: { message: 'Session error' }
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('error')).toHaveTextContent('Session error')
  })

  it('should handle sign in successfully', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signInWithPassword.mockResolvedValue({
      data: { user: {
        id: 'user123',
        email: 'test@example.com',
        app_metadata: {},
        user_metadata: { full_name: 'Test User' },
        aud: 'authenticated',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }, session: { access_token: 'token' } },
      error: null
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signInButton = screen.getByText('Sign In')
    await user.click(signInButton)

    await waitFor(() => {
      expect(mockSupabase.auth.signInWithPassword).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password'
      })
    })
  })

  it('should handle sign in error', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signInWithPassword.mockResolvedValue({
      data: { user: null, session: null },
      error: { message: 'Invalid credentials' }
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signInButton = screen.getByText('Sign In')
    await user.click(signInButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Invalid credentials')
    })
  })

  it('should handle sign in exception', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signInWithPassword.mockRejectedValue(new Error('Network error'))
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signInButton = screen.getByText('Sign In')
    await user.click(signInButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Network error')
    })
  })

  it('should handle sign in with non-Error exception', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signInWithPassword.mockRejectedValue('String error')
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signInButton = screen.getByText('Sign In')
    await user.click(signInButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Failed to sign in')
    })
  })

  it('should handle sign up successfully', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signUp.mockResolvedValue({
      data: { user: {
        id: 'user123',
        email: 'test@example.com',
        app_metadata: {},
        user_metadata: { full_name: 'Test User' },
        aud: 'authenticated',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }, session: { access_token: 'token' } },
      error: null
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signUpButton = screen.getByText('Sign Up')
    await user.click(signUpButton)

    await waitFor(() => {
      expect(mockSupabase.auth.signUp).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password',
        options: {
          data: { full_name: 'Test User' }
        }
      })
    })
  })

  it('should handle sign up without full name', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signUp.mockResolvedValue({
      data: { user: {
        id: 'user123',
        email: 'test@example.com',
        app_metadata: {},
        user_metadata: { full_name: 'Test User' },
        aud: 'authenticated',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }, session: { access_token: 'token' } },
      error: null
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signUpButton = screen.getByText('Sign Up No Name')
    await user.click(signUpButton)

    await waitFor(() => {
      expect(mockSupabase.auth.signUp).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password',
        options: {
          data: { full_name: undefined }
        }
      })
    })
  })

  it('should handle sign up error', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signUp.mockResolvedValue({
      data: { user: null, session: null },
      error: { message: 'User already exists' }
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signUpButton = screen.getByText('Sign Up')
    await user.click(signUpButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('User already exists')
    })
  })

  it('should handle sign up exception', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signUp.mockRejectedValue(new Error('Network error'))
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signUpButton = screen.getByText('Sign Up')
    await user.click(signUpButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Network error')
    })
  })

  it('should handle sign up with non-Error exception', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signUp.mockRejectedValue('String error')
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signUpButton = screen.getByText('Sign Up')
    await user.click(signUpButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Failed to sign up')
    })
  })

  it('should handle sign out successfully', async () => {
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { user: mockUser }, 
      error: null 
    })
    mockSupabase.auth.signOut.mockResolvedValue({ error: null })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    const signOutButton = screen.getByText('Sign Out')
    await user.click(signOutButton)

    await waitFor(() => {
      expect(mockSupabase.auth.signOut).toHaveBeenCalled()
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  it('should handle sign out error', async () => {
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { user: mockUser }, 
      error: null 
    })
    mockSupabase.auth.signOut.mockResolvedValue({ error: { message: 'Sign out failed' } })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    const signOutButton = screen.getByText('Sign Out')
    await user.click(signOutButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Sign out failed')
    })
  })

  it('should handle sign out exception', async () => {
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { user: mockUser }, 
      error: null 
    })
    mockSupabase.auth.signOut.mockRejectedValue(new Error('Network error'))
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    const signOutButton = screen.getByText('Sign Out')
    await user.click(signOutButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Network error')
    })
  })

  it('should handle sign out with non-Error exception', async () => {
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { user: mockUser }, 
      error: null 
    })
    mockSupabase.auth.signOut.mockRejectedValue('String error')
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    const signOutButton = screen.getByText('Sign Out')
    await user.click(signOutButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Failed to sign out')
    })
  })

  it('should handle auth state changes', async () => {
    let authChangeCallback: any = null
    
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.onAuthStateChange.mockImplementation((callback) => {
      authChangeCallback = callback
      return {
        data: { subscription: { unsubscribe: vi.fn() } }
      }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    // Simulate auth state change
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    act(() => {
      authChangeCallback('SIGNED_IN', { user: mockUser })
    })

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com')
    })

    // Simulate sign out
    act(() => {
      authChangeCallback('SIGNED_OUT', { user: null })
    })

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
      expect(screen.getByTestId('user')).toHaveTextContent('No user')
    })
  })

  it('should handle auth state changes without session', async () => {
    let authChangeCallback: any = null
    
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.onAuthStateChange.mockImplementation((callback) => {
      authChangeCallback = callback
      return {
        data: { subscription: { unsubscribe: vi.fn() } }
      }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    // Simulate auth state change without session
    act(() => {
      authChangeCallback('SIGNED_OUT', null)
    })

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
      expect(screen.getByTestId('user')).toHaveTextContent('No user')
    })
  })

  it('should handle refresh user successfully', async () => {
    const mockUser: SupabaseUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: mockUser }, error: null })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const refreshButton = screen.getByText('Refresh')
    await user.click(refreshButton)

    await waitFor(() => {
      expect(mockSupabase.auth.getUser).toHaveBeenCalled()
      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com')
    })
  })

  it('should handle refresh user with no user', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const refreshButton = screen.getByText('Refresh')
    await user.click(refreshButton)

    await waitFor(() => {
      expect(mockSupabase.auth.getUser).toHaveBeenCalled()
      expect(screen.getByTestId('user')).toHaveTextContent('No user')
    })
  })

  it('should handle refresh user error', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.getUser.mockResolvedValue({ 
      data: { user: null }, 
      error: { message: 'User fetch failed' }
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const refreshButton = screen.getByText('Refresh')
    await user.click(refreshButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('User fetch failed')
    })
  })

  it('should handle refresh user exception', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.getUser.mockRejectedValue(new Error('Network error'))
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const refreshButton = screen.getByText('Refresh')
    await user.click(refreshButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Network error')
    })
  })

  it('should handle refresh user with non-Error exception', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.getUser.mockRejectedValue('String error')
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const refreshButton = screen.getByText('Refresh')
    await user.click(refreshButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Failed to refresh user')
    })
  })

  it('should clear error', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.signInWithPassword.mockResolvedValue({
      data: { user: null, session: null },
      error: { message: 'Test error' }
    })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } }
    })

    const user = userEvent.setup()
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    // Trigger error
    const signInButton = screen.getByText('Sign In')
    await user.click(signInButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Test error')
    })

    // Clear error
    const clearButton = screen.getByText('Clear Error')
    await user.click(clearButton)

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('No error')
    })
  })

  it('should unsubscribe from auth changes on unmount', async () => {
    const unsubscribeFn = vi.fn()
    
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null })
    mockSupabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: unsubscribeFn } }
    })

    const { unmount } = render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    unmount()

    expect(unsubscribeFn).toHaveBeenCalled()
  })

  it('should throw error when useAuth is used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    expect(() => {
      render(<TestComponent />)
    }).toThrow('useAuth must be used within an AuthProvider')
    
    consoleSpy.mockRestore()
  })
})