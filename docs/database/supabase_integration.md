# Supabase Integration

This document outlines the strategy and implementation details for integrating Supabase with the TripSage travel planning system.

## 1. Overview

TripSage uses Supabase as its primary database solution, providing a PostgreSQL database with built-in authentication, real-time capabilities, and storage. This integration forms the foundation of the dual storage architecture, complemented by the knowledge graph maintained by the Memory MCP Server.

## 2. Project Configuration

### Supabase Project Setup

**Project Name:** tripsage_planner

**Region:** Select the closest region to your primary user base or development team (e.g., us-west-1 for US West)

**Database Password:** Use a strong, generated password stored securely in password management

**Pricing Plan:** Start with the free tier for development, upgrade to Pro for production

### Environment Variables

Essential environment variables for connecting to Supabase:

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

The `NEXT_PUBLIC_` prefix makes the variables available to client-side code. The service role key must be kept server-side only.

## 3. Database Schema

TripSage implements a carefully designed schema to support travel planning functionality. The core tables are defined below, with complete SQL definitions available in the migrations directory.

### Core Tables

#### users

Stores user profiles and preferences

```sql
CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT,
    email TEXT,
    preferences_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT users_email_unique UNIQUE (email)
);
```

#### trips

Stores trip details including destination, dates, and budget

```sql
CREATE TABLE trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT NOT NULL,
    budget NUMERIC NOT NULL,
    travelers INTEGER NOT NULL,
    status TEXT NOT NULL,
    trip_type TEXT NOT NULL,
    flexibility JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT trips_date_check CHECK (end_date >= start_date),
    CONSTRAINT trips_travelers_check CHECK (travelers > 0),
    CONSTRAINT trips_budget_check CHECK (budget > 0),
    CONSTRAINT trips_status_check CHECK (status IN ('planning', 'booked', 'completed', 'canceled')),
    CONSTRAINT trips_type_check CHECK (trip_type IN ('leisure', 'business', 'family', 'solo', 'other'))
);
```

#### flights

Stores flight information for trips

```sql
CREATE TABLE flights (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT REFERENCES trips(id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    airline TEXT,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    booking_link TEXT,
    segment_number INTEGER,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    booking_status TEXT DEFAULT 'saved',
    data_source TEXT,
    CONSTRAINT flights_price_check CHECK (price >= 0)
);
```

#### accommodations

Stores accommodation options for trips

```sql
CREATE TABLE accommodations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT REFERENCES trips(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    price_per_night NUMERIC NOT NULL,
    total_price NUMERIC NOT NULL,
    location TEXT NOT NULL,
    rating NUMERIC,
    amenities JSONB,
    booking_link TEXT,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    booking_status TEXT DEFAULT 'saved',
    cancellation_policy TEXT,
    distance_to_center NUMERIC,
    neighborhood TEXT,
    CONSTRAINT accommodations_price_check CHECK (price_per_night >= 0),
    CONSTRAINT accommodations_total_price_check CHECK (total_price >= 0),
    CONSTRAINT accommodations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5))
);
```

### Additional Tables

TripSage's schema includes these additional tables to support comprehensive travel planning:

- **transportation**: Local transportation options during trips
- **itinerary_items**: Daily activities and events
- **search_parameters**: Records of search criteria for result comparison
- **price_history**: Historical price data for trend analysis
- **trip_notes**: User notes attached to trips
- **saved_options**: Options marked as favorites by users
- **trip_comparison**: Comparison data between alternative trip plans

## 4. TypeScript Integration

TripSage uses TypeScript to provide strong typing for database interactions. The Supabase type definitions are stored in `src/types/supabase.ts`.

### Type Definitions

```typescript
// Example of type definitions
export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: number;
          name: string | null;
          email: string | null;
          preferences_json: Json | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          name?: string | null;
          email?: string | null;
          preferences_json?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          name?: string | null;
          email?: string | null;
          preferences_json?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Relationships: [];
      };
      // Additional table definitions...
    };
  };
}

// Type aliases for easier usage
export type User = Database["public"]["Tables"]["users"]["Row"];
export type Trip = Database["public"]["Tables"]["trips"]["Row"];
export type Flight = Database["public"]["Tables"]["flights"]["Row"];
// Additional type aliases...
```

### Type Generation

The types can be automatically generated from the database schema using the Supabase CLI:

```bash
supabase gen types typescript --project-id your-project-id > src/types/supabase.ts
```

## 5. Frontend Integration

### Client Setup

The Next.js frontend uses two approaches for connecting to Supabase:

1. **Server-Side Client**: For use in Server Components and API routes

```typescript
// lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { Database } from '@/types/supabase';

export function createServerSupabaseClient() {
  const cookieStore = cookies();

  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value;
        },
        set(name: string, value: string, options: { path: string; maxAge: number; sameSite: string; }) {
          cookieStore.set({ name, value, ...options });
        },
        remove(name: string, options: { path: string; }) {
          cookieStore.set({ name, value: '', ...options, maxAge: 0 });
        },
      },
    }
  );
}
```

2. **Client-Side Client**: For use in Client Components with hooks

```typescript
// lib/supabase/client.ts
'use client';

import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { Database } from '@/types/supabase';

export function createClientSupabaseClient() {
  return createClientComponentClient<Database>({
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL!,
    supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  });
}
```

### Authentication Integration

TripSage implements Supabase authentication with middleware for session management:

```typescript
// middleware.ts
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import type { Database } from '@/types/supabase';

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient<Database>({ req, res });

  // Refresh session if expired
  const { data: { session } } = await supabase.auth.getSession();

  // Redirect to login if accessing protected routes without session
  if (!session && req.nextUrl.pathname.startsWith('/app')) {
    return NextResponse.redirect(new URL('/auth/login', req.url));
  }

  return res;
}

export const config = {
  matcher: [
    '/app/:path*',
    '/api/:path*',
  ],
};
```

## 6. Backend Integration

### MCP Server Integration

The Supabase MCP Server provides a standardized interface for Supabase operations. It exposes the following tools:

- **list_projects**: Lists all available Supabase projects
- **list_tables**: Lists tables in the database
- **execute_sql**: Executes SQL queries
- **generate_typescript_types**: Generates TypeScript type definitions

The server uses the Supabase Management API for administrative operations and the Supabase JavaScript client for data operations.

```typescript
// Example implementation of a Supabase MCP tool
@mcp.tool()
async function execute_sql(
  { project_id, query }: { project_id: string, query: string }
): Promise<SqlResult> {
  try {
    // Initialize Supabase client with service role key
    const supabase = createClient(
      `https://${project_id}.supabase.co`,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );
    
    // Execute the SQL query
    const { data, error } = await supabase.rpc('exec_sql', { query });
    
    if (error) throw error;
    
    return {
      success: true,
      data: data
    };
  } catch (error) {
    console.error('SQL execution error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}
```

### API Integration

The Next.js API routes integrate with Supabase for data operations:

```typescript
// app/api/trips/route.ts
import { createServerSupabaseClient } from '@/lib/supabase/server';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  try {
    const supabase = createServerSupabaseClient();
    
    // Get the user from the session
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    
    // Fetch trips for the current user
    const { data: trips, error } = await supabase
      .from('trips')
      .select('*')
      .order('created_at', { ascending: false });
    
    if (error) throw error;
    
    return NextResponse.json({ trips });
  } catch (error) {
    console.error('Error fetching trips:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
```

## 7. Security Implementation

### Row-Level Security (RLS)

Supabase enables row-level security for protecting user data. TripSage implements these RLS policies:

```sql
-- Enable RLS on users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Users can only read and update their own profile
CREATE POLICY users_policy_select ON users
  FOR SELECT
  USING (auth.uid() = id::text);

CREATE POLICY users_policy_update ON users
  FOR UPDATE
  USING (auth.uid() = id::text);

-- Similar policies for trips and related tables
-- Ensure trips can only be accessed by their creator
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;

CREATE POLICY trips_policy_select ON trips
  FOR SELECT
  USING (auth.uid() = user_id::text);

CREATE POLICY trips_policy_insert ON trips
  FOR INSERT
  WITH CHECK (auth.uid() = user_id::text);

CREATE POLICY trips_policy_update ON trips
  FOR UPDATE
  USING (auth.uid() = user_id::text);

CREATE POLICY trips_policy_delete ON trips
  FOR DELETE
  USING (auth.uid() = user_id::text);
```

### API Key Management

TripSage manages Supabase API keys securely:

1. **Public Anon Key**: Used for client-side operations with limited permissions
2. **Service Role Key**: Used only in trusted server environments for admin operations
3. **Key Rotation**: Implement regular key rotation through CI/CD pipelines

## 8. Real-time Features

TripSage leverages Supabase's real-time capabilities for collaborative trip planning:

```typescript
// Example of real-time subscription
'use client';

import { useEffect, useState } from 'react';
import { createClientSupabaseClient } from '@/lib/supabase/client';
import type { Trip } from '@/types/supabase';

export function useTripUpdates(tripId: number) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const supabase = createClientSupabaseClient();
  
  useEffect(() => {
    // Initial fetch
    const fetchTrip = async () => {
      const { data } = await supabase
        .from('trips')
        .select('*')
        .eq('id', tripId)
        .single();
      
      if (data) setTrip(data);
    };
    
    fetchTrip();
    
    // Set up real-time subscription
    const subscription = supabase
      .channel(`trip-${tripId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'trips',
          filter: `id=eq.${tripId}`
        },
        (payload) => {
          setTrip(payload.new as Trip);
        }
      )
      .subscribe();
    
    return () => {
      supabase.removeChannel(subscription);
    };
  }, [tripId, supabase]);
  
  return trip;
}
```

## 9. Data Migration Strategy

TripSage uses a structured approach to database migrations:

1. **Migration Scripts**: SQL migration scripts in the `/migrations` directory follow a naming convention `YYYYMMDD_XX_description.sql`
2. **Supabase Migrations**: Use the Supabase CLI to apply migrations:

```bash
supabase migration up
```

3. **Seed Data**: Initial data is provided through seed scripts for testing and development:

```bash
supabase db seed
```

## 10. Performance Optimization

### Indexing Strategy

TripSage implements these indexes for optimized query performance:

```sql
-- Improve search performance on trips
CREATE INDEX idx_trips_destination ON trips USING gin (to_tsvector('english', destination));
CREATE INDEX idx_trips_dates ON trips (start_date, end_date);

-- Improve performance for flight searches
CREATE INDEX idx_flights_origin_destination ON flights (origin, destination);
CREATE INDEX idx_flights_departure_time ON flights (departure_time);

-- Improve performance for accommodation location searches
CREATE INDEX idx_accommodations_location ON accommodations USING gin (to_tsvector('english', location));
```

### Query Optimization

Frontend and backend components follow these query optimization practices:

1. **Select Only Needed Columns**: Avoid `SELECT *` when possible
2. **Use Pagination**: For listings with many results
3. **Join Relations Efficiently**: Use the Supabase `.select()` with relationship expansion

```typescript
// Example of optimized query with relationship expansion
const { data: trips } = await supabase
  .from('trips')
  .select(`
    id,
    name,
    destination,
    start_date,
    end_date,
    flights (id, airline, departure_time, arrival_time)
  `)
  .order('start_date', { ascending: true })
  .range(0, 9); // Pagination for first 10 results
```

### Caching Strategy

TripSage implements the following caching mechanisms:

1. **Client-Side Caching**: Using React Query for client-side data caching:

```typescript
// Example of React Query usage with Supabase
import { useQuery } from '@tanstack/react-query';
import { createClientSupabaseClient } from '@/lib/supabase/client';

export function useTrips() {
  const supabase = createClientSupabaseClient();
  
  return useQuery({
    queryKey: ['trips'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('trips')
        .select('*')
        .order('created_at', { ascending: false });
      
      if (error) throw error;
      return data;
    },
    staleTime: 60000, // 1 minute
  });
}
```

2. **Edge Caching**: For public, non-personalized data like destination information

## 11. Monitoring and Logging

TripSage implements comprehensive monitoring for Supabase:

1. **Database Query Logging**: Enabled for development, sampling for production
2. **Performance Monitoring**: Track query performance and slow queries
3. **Error Tracking**: Capture and report database errors with context

```typescript
// Example error tracking middleware
async function withErrorTracking(req, res, next) {
  try {
    await next();
  } catch (error) {
    if (error.code === 'PGRST116') {
      // Handle foreign key constraint errors
      console.error('Database foreign key constraint error:', error);
      Sentry.captureException(error, {
        extra: {
          endpoint: req.url,
          userId: req.user?.id,
          payload: req.body
        }
      });
    }
    
    throw error;
  }
}
```

## 12. Testing Strategy

TripSage's Supabase integration includes these testing approaches:

1. **Local Testing**: Use Supabase Local Development for unit and integration tests
2. **Mock Supabase Client**: For component testing

```typescript
// Example of mocking Supabase for tests
jest.mock('@/lib/supabase/client', () => ({
  createClientSupabaseClient: () => ({
    from: jest.fn().mockReturnThis(),
    select: jest.fn().mockReturnThis(),
    eq: jest.fn().mockReturnThis(),
    single: jest.fn().mockResolvedValue({
      data: {
        id: 1,
        name: 'Test Trip',
        destination: 'Paris',
        start_date: '2025-06-01',
        end_date: '2025-06-07'
      },
      error: null
    })
  })
}));
```

3. **E2E Testing**: Using Playwright with a test database

## 13. Backup and Disaster Recovery

TripSage implements the following backup strategy:

1. **Automated Backups**: Daily automated database backups
2. **Point-in-Time Recovery**: Enabled for production database
3. **Backup Verification**: Weekly verification of backup integrity

## Conclusion

This document outlines the comprehensive strategy for integrating Supabase with the TripSage travel planning system. By leveraging Supabase's powerful features, TripSage provides a secure, scalable, and real-time enabled application that meets the needs of travel planning users.

The integration of Supabase with the Memory MCP Server (knowledge graph) creates a dual storage architecture that balances structured relational data with flexible semantic relationships, providing the best of both worlds for travel data management.

## References

1. [Supabase Documentation](https://supabase.com/docs)
2. [Next.js with Supabase Guide](https://supabase.com/docs/guides/getting-started/tutorials/with-nextjs)
3. [Supabase Auth Helpers for Next.js](https://supabase.com/docs/guides/auth/auth-helpers/nextjs)
4. [Supabase Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
5. [React Query Documentation](https://tanstack.com/query/latest/docs/react/overview)