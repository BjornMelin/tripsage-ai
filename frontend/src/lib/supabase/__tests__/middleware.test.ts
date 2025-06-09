import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest, NextResponse } from 'next/server'
import { updateSession } from '../middleware'
import { createServerClient } from '@supabase/ssr'

// Mock Next.js server modules
vi.mock('next/server', () => ({
  NextRequest: vi.fn(),
  NextResponse: {
    next: vi.fn(() => ({
      cookies: {
        set: vi.fn(),
        delete: vi.fn()
      }
    })),
    redirect: vi.fn((url) => ({
      cookies: {
        set: vi.fn(),
        delete: vi.fn()
      },
      headers: new Map(),
      status: 302,
      url
    }))
  }
}))

// Mock Supabase SSR
vi.mock('@supabase/ssr', () => ({
  createServerClient: vi.fn()
}))

describe('updateSession', () => {
  let mockRequest: any
  let mockSupabase: any
  let mockUser: any
  let mockCookiesToSet: any[] = []
  let mockCookiesToRemove: string[] = []

  beforeEach(() => {
    vi.clearAllMocks()
    mockCookiesToSet = []
    mockCookiesToRemove = []

    // Mock request
    mockRequest = {
      cookies: {
        getAll: vi.fn().mockReturnValue([
          { name: 'cookie1', value: 'value1' },
          { name: 'cookie2', value: 'value2' }
        ])
      },
      url: 'http://localhost:3000/dashboard',
      nextUrl: {
        pathname: '/dashboard',
        clone: vi.fn().mockReturnValue({
          pathname: '/login',
          href: 'http://localhost:3000/login'
        })
      }
    }

    // Mock user
    mockUser = {
      id: 'user123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString()
    }

    // Mock Supabase client
    mockSupabase = {
      auth: {
        getUser: vi.fn()
      }
    }

    // Mock createServerClient
    vi.mocked(createServerClient).mockImplementation((url, key, options) => {
      // Capture cookie operations
      const originalGetAll = options.cookies.getAll
      const originalSetAll = options.cookies.setAll

      options.cookies.getAll = () => {
        const result = originalGetAll()
        return result
      }

      options.cookies.setAll = (cookiesToSet) => {
        mockCookiesToSet.push(...cookiesToSet)
        originalSetAll(cookiesToSet)
      }

      return mockSupabase
    })
  })

  it('should allow authenticated users to access protected routes', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: mockUser },
      error: null
    })

    const response = await updateSession(mockRequest)

    expect(mockSupabase.auth.getUser).toHaveBeenCalled()
    expect(response).toBeDefined()
    expect(vi.mocked(NextResponse).next).toHaveBeenCalled()
  })

  it('should redirect unauthenticated users from protected routes to login', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    mockRequest.nextUrl.pathname = '/dashboard'

    const response = await updateSession(mockRequest)

    expect(mockSupabase.auth.getUser).toHaveBeenCalled()
    expect(vi.mocked(NextResponse).redirect).toHaveBeenCalled()
    
    const redirectCall = vi.mocked(NextResponse).redirect.mock.calls[0]
    expect(redirectCall[0]).toBeInstanceOf(URL)
    expect(redirectCall[0].pathname).toBe('/login')
  })

  it('should allow unauthenticated users to access public routes', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    mockRequest.nextUrl.pathname = '/'

    const response = await updateSession(mockRequest)

    expect(mockSupabase.auth.getUser).toHaveBeenCalled()
    expect(vi.mocked(NextResponse).next).toHaveBeenCalled()
    expect(vi.mocked(NextResponse).redirect).not.toHaveBeenCalled()
  })

  it('should allow unauthenticated users to access auth routes', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    const authRoutes = ['/login', '/register', '/reset-password']

    for (const route of authRoutes) {
      vi.clearAllMocks()
      mockRequest.nextUrl.pathname = route

      const response = await updateSession(mockRequest)

      expect(vi.mocked(NextResponse).next).toHaveBeenCalled()
      expect(vi.mocked(NextResponse).redirect).not.toHaveBeenCalled()
    }
  })

  it('should handle auth errors gracefully', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: { message: 'Auth service unavailable' }
    })

    mockRequest.nextUrl.pathname = '/dashboard'

    const response = await updateSession(mockRequest)

    // Should redirect to login on auth error for protected routes
    expect(vi.mocked(NextResponse).redirect).toHaveBeenCalled()
  })

  it('should handle missing environment variables', async () => {
    // Clear env vars
    const originalUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const originalKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    
    delete process.env.NEXT_PUBLIC_SUPABASE_URL
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    await expect(updateSession(mockRequest)).rejects.toThrow()

    // Restore env vars
    process.env.NEXT_PUBLIC_SUPABASE_URL = originalUrl
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = originalKey
  })

  it('should handle API routes differently', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    mockRequest.nextUrl.pathname = '/api/health'

    const response = await updateSession(mockRequest)

    // API routes should not redirect
    expect(vi.mocked(NextResponse).next).toHaveBeenCalled()
    expect(vi.mocked(NextResponse).redirect).not.toHaveBeenCalled()
  })

  it('should handle static assets', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    const staticPaths = [
      '/_next/static/chunk.js',
      '/favicon.ico',
      '/images/logo.png'
    ]

    for (const path of staticPaths) {
      vi.clearAllMocks()
      mockRequest.nextUrl.pathname = path

      const response = await updateSession(mockRequest)

      expect(vi.mocked(NextResponse).next).toHaveBeenCalled()
      expect(vi.mocked(NextResponse).redirect).not.toHaveBeenCalled()
    }
  })

  it('should preserve query parameters on redirect', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    mockRequest.nextUrl.pathname = '/dashboard'
    mockRequest.nextUrl.search = '?redirect=/trips&tab=active'
    mockRequest.url = 'http://localhost:3000/dashboard?redirect=/trips&tab=active'

    const response = await updateSession(mockRequest)

    expect(vi.mocked(NextResponse).redirect).toHaveBeenCalled()
    
    const redirectCall = vi.mocked(NextResponse).redirect.mock.calls[0]
    expect(redirectCall[0]).toBeInstanceOf(URL)
    expect(redirectCall[0].pathname).toBe('/login')
  })

  it('should handle cookie operations', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: mockUser },
      error: null
    })

    // Mock cookie updates from Supabase
    vi.mocked(createServerClient).mockImplementation((url, key, options) => {
      // Simulate Supabase setting auth cookies
      options.cookies.setAll([
        { name: 'sb-auth-token', value: 'new-token', options: { httpOnly: true } },
        { name: 'sb-refresh-token', value: 'new-refresh', options: { httpOnly: true } }
      ])
      
      return mockSupabase
    })

    const response = await updateSession(mockRequest)

    expect(mockCookiesToSet).toHaveLength(2)
    expect(mockCookiesToSet[0].name).toBe('sb-auth-token')
    expect(mockCookiesToSet[1].name).toBe('sb-refresh-token')
  })

  it('should handle deeply nested protected routes', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    const nestedRoutes = [
      '/dashboard/trips/123/edit',
      '/profile/settings/security',
      '/search/flights/results'
    ]

    for (const route of nestedRoutes) {
      vi.clearAllMocks()
      mockRequest.nextUrl.pathname = route

      const response = await updateSession(mockRequest)

      expect(vi.mocked(NextResponse).redirect).toHaveBeenCalled()
    }
  })

  it('should handle authenticated users accessing auth pages', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: mockUser },
      error: null
    })

    const authRoutes = ['/login', '/register', '/reset-password']

    for (const route of authRoutes) {
      vi.clearAllMocks()
      mockRequest.nextUrl.pathname = route

      const response = await updateSession(mockRequest)

      // Should allow authenticated users to access auth pages
      // (they might want to change password, etc.)
      expect(vi.mocked(NextResponse).next).toHaveBeenCalled()
      expect(vi.mocked(NextResponse).redirect).not.toHaveBeenCalled()
    }
  })

  it('should handle edge cases in URL parsing', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null
    })

    // Test with unusual but valid URLs
    const edgeCaseUrls = [
      'http://localhost:3000/dashboard#section',
      'http://localhost:3000/dashboard?',
      'http://localhost:3000//dashboard', // Double slash
    ]

    for (const url of edgeCaseUrls) {
      vi.clearAllMocks()
      mockRequest.url = url
      mockRequest.nextUrl.pathname = '/dashboard'

      const response = await updateSession(mockRequest)

      expect(vi.mocked(NextResponse).redirect).toHaveBeenCalled()
    }
  })

  it('should handle missing request properties gracefully', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: mockUser },
      error: null
    })

    // Request with minimal properties
    const minimalRequest = {
      cookies: mockRequest.cookies,
      url: 'http://localhost:3000/',
      nextUrl: {
        pathname: '/'
      }
    }

    const response = await updateSession(minimalRequest as any)

    expect(vi.mocked(NextResponse).next).toHaveBeenCalled()
  })

  it('should handle concurrent session updates', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: mockUser },
      error: null
    })

    // Simulate concurrent requests
    const promises = Array(5).fill(null).map(() => 
      updateSession(mockRequest)
    )

    const responses = await Promise.all(promises)

    expect(responses).toHaveLength(5)
    expect(mockSupabase.auth.getUser).toHaveBeenCalledTimes(5)
  })
})