# Supabase Integration Guide for TripSage

This guide covers the integration of Supabase with Next.js 15 App Router for authentication, real-time subscriptions, and database operations.

## Setup

### 1. Install Dependencies

```bash
pnpm add @supabase/supabase-js @supabase/ssr
```

### 2. Environment Variables

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

### 3. Supabase Client Configuration

Create utilities for server and client-side usage:

#### Server Client (`src/lib/supabase/server.ts`)

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import type { Database } from '@/types/database'

export async function createServerSupabaseClient() {
  const cookieStore = await cookies()
  
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
        set(name: string, value: string, options: any) {
          cookieStore.set(name, value, options)
        },
        remove(name: string, options: any) {
          cookieStore.delete(name, options)
        },
      },
    }
  )
}
```

#### Browser Client (`src/lib/supabase/client.ts`)

```typescript
import { createBrowserClient } from '@supabase/ssr'
import type { Database } from '@/types/database'

export function createBrowserSupabaseClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

## Authentication

### Login Component

```typescript
'use client'

import { useState } from 'react'
import { createBrowserSupabaseClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Icons } from '@/components/icons'

export function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const supabase = createBrowserSupabaseClient()

  async function handleEmailLogin() {
    try {
      setLoading(true)
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      if (error) throw error
    } catch (error) {
      console.error('Error logging in:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogleLogin() {
    try {
      setLoading(true)
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      })
      if (error) throw error
    } catch (error) {
      console.error('Error logging in with Google:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <Input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={loading}
      />
      <Input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={loading}
      />
      <Button
        onClick={handleEmailLogin}
        disabled={loading}
        className="w-full"
      >
        {loading ? <Icons.spinner className="animate-spin" /> : 'Sign In'}
      </Button>
      <Button
        onClick={handleGoogleLogin}
        variant="outline"
        disabled={loading}
        className="w-full"
      >
        <Icons.google className="mr-2 h-4 w-4" />
        Sign in with Google
      </Button>
    </div>
  )
}
```

### Middleware for Protected Routes

```typescript
// src/middleware.ts
import { createServerSupabaseClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  const response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  const supabase = await createServerSupabaseClient()

  const {
    data: { session },
  } = await supabase.auth.getSession()

  // Protected routes pattern
  const isProtectedRoute = request.nextUrl.pathname.startsWith('/dashboard')
  const isAuthRoute = request.nextUrl.pathname.startsWith('/auth')

  if (isProtectedRoute && !session) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  if (isAuthRoute && session) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
```

## Real-time Subscriptions

### Trip Updates Component

```typescript
'use client'

import { useEffect, useState } from 'react'
import { createBrowserSupabaseClient } from '@/lib/supabase/client'
import type { RealtimeChannel } from '@supabase/supabase-js'
import type { Trip } from '@/types/trip'

export function TripRealtimeUpdates({ tripId }: { tripId: string }) {
  const [trip, setTrip] = useState<Trip | null>(null)
  const supabase = createBrowserSupabaseClient()

  useEffect(() => {
    let channel: RealtimeChannel

    async function setupRealtime() {
      // Initial fetch
      const { data } = await supabase
        .from('trips')
        .select('*')
        .eq('id', tripId)
        .single()
      
      if (data) setTrip(data)

      // Subscribe to changes
      channel = supabase
        .channel(`trip:${tripId}`)
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'trips',
            filter: `id=eq.${tripId}`,
          },
          (payload) => {
            console.log('Trip updated:', payload)
            if (payload.eventType === 'UPDATE') {
              setTrip(payload.new as Trip)
            }
          }
        )
        .subscribe()
    }

    setupRealtime()

    return () => {
      if (channel) supabase.removeChannel(channel)
    }
  }, [tripId, supabase])

  if (!trip) return <div>Loading...</div>

  return (
    <div>
      <h2>{trip.name}</h2>
      <p>Status: {trip.status}</p>
      {/* Trip details */}
    </div>
  )
}
```

## Database Operations

### CRUD Operations

```typescript
// Server Component
import { createServerSupabaseClient } from '@/lib/supabase/server'

export default async function TripsPage() {
  const supabase = await createServerSupabaseClient()
  
  // Fetch trips
  const { data: trips, error } = await supabase
    .from('trips')
    .select(`
      *,
      destinations(*),
      accommodations(*),
      activities(*)
    `)
    .order('created_at', { ascending: false })

  if (error) {
    console.error('Error fetching trips:', error)
    return <div>Error loading trips</div>
  }

  return (
    <div>
      {trips?.map((trip) => (
        <TripCard key={trip.id} trip={trip} />
      ))}
    </div>
  )
}
```

### Row Level Security (RLS)

Enable RLS for your tables and create policies:

```sql
-- Enable RLS on trips table
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;

-- Create policy for users to see only their trips
CREATE POLICY "Users can view own trips" ON trips
FOR SELECT USING (auth.uid() = user_id);

-- Create policy for users to insert their own trips
CREATE POLICY "Users can insert own trips" ON trips
FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Create policy for users to update their own trips
CREATE POLICY "Users can update own trips" ON trips
FOR UPDATE USING (auth.uid() = user_id);
```

## Type Generation

Generate TypeScript types from your database schema:

```bash
pnpm supabase gen types typescript --local > src/types/database.ts
```

## Edge Functions Integration

Create an edge function for complex operations:

```typescript
// supabase/functions/process-trip/index.ts
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  const { tripId, action } = await req.json()
  
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )

  // Process trip
  const { data, error } = await supabase
    .from('trips')
    .update({ status: 'processing' })
    .eq('id', tripId)
    .select()

  return new Response(
    JSON.stringify({ success: !error, data }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
```

## Best Practices

1. **Use Server Components for Initial Data**: Fetch data in Server Components when possible
2. **Client-side for Real-time**: Use Client Components for real-time subscriptions
3. **Type Safety**: Always use generated TypeScript types
4. **Error Handling**: Implement proper error boundaries and fallbacks
5. **Security**: Use RLS policies and never expose service role keys
6. **Caching**: Leverage Next.js caching with proper revalidation

## Integration with TripSage

### Trip Storage Service

```typescript
import { createServerSupabaseClient } from '@/lib/supabase/server'
import type { Trip, TripCreateInput } from '@/types/trip'

export class SupabaseTripService {
  private supabase

  constructor() {
    this.supabase = createServerSupabaseClient()
  }

  async createTrip(input: TripCreateInput): Promise<Trip> {
    const { data, error } = await this.supabase
      .from('trips')
      .insert(input)
      .select()
      .single()

    if (error) throw error
    return data
  }

  async getTrip(id: string): Promise<Trip | null> {
    const { data, error } = await this.supabase
      .from('trips')
      .select('*, destinations(*), accommodations(*)')
      .eq('id', id)
      .single()

    if (error) return null
    return data
  }

  async updateTrip(id: string, updates: Partial<Trip>): Promise<Trip> {
    const { data, error } = await this.supabase
      .from('trips')
      .update(updates)
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    return data
  }
}
```

This integration ensures seamless data flow between TripSage's AI agents and the persistent storage layer.