# TripSage Relational Database Guide (Supabase & Neon)

This document provides a comprehensive guide to setting up, configuring, and interacting with the relational databases (PostgreSQL) used in the TripSage system. TripSage employs a dual-provider strategy for its relational database needs: Supabase for production and staging environments, and Neon for development and testing environments.

## 1. Overview of Relational Database Strategy

TripSage utilizes PostgreSQL as its relational database. To optimize for different stages of the development lifecycle, two managed PostgreSQL providers are used:

- **Supabase (Production & Staging)**:
  - Provides a robust, managed PostgreSQL database with integrated services like authentication, real-time capabilities, and storage.
  - Offers excellent Row-Level Security (RLS) tools, crucial for production data protection.
  - Generally better cold start performance suitable for production workloads.
- **Neon (Development & Testing)**:
  - A serverless PostgreSQL platform with powerful branching capabilities.
  - Allows each developer or feature branch to have its own isolated, instantly-creatable database instance.
  - Offers a generous free tier with unlimited projects, ideal for development.

Both Supabase and Neon are accessed primarily through a **Model Context Protocol (MCP) abstraction layer**. This means that direct database client connections in the application code are minimized, and interactions are standardized through database-specific MCP servers or tools.

## 2. Project Setup and Configuration

### 2.1 Supabase Project Setup (Production/Staging)

- **Project Name**: `tripsage_planner` (or environment-specific like `tripsage_planner_staging`)
- **Region**: Choose a region closest to your primary user base or backend services (e.g., `us-east-1`, `us-west-2`).
- **Database Password**: Use a strong, generated password, stored securely (e.g., in a secrets manager).
- **Pricing Plan**: Start with the free tier for initial staging/testing, upgrade to a Pro or higher tier for production workloads based on resource needs.

### 2.2 Neon Project Setup (Development)

- Sign up at [Neon](https://neon.tech/).
- Create a new project (e.g., `tripsage-dev`).
- Neon's serverless nature means resources scale automatically, and branching is a core feature.

### 2.3 Environment Variables

Essential environment variables for connecting to the databases and their respective MCPs:

**For Direct Supabase Connection (primarily for migrations, initial setup, or specific admin tasks):**

````plaintext
# .env example for Supabase direct access
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-public-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key # Keep this highly secure, server-side only```

**For Supabase MCP (Production/Staging Environment MCP Interaction):**
```plaintext
# .env example for Supabase MCP
TRIPSAGE_MCP_SUPABASE_ENDPOINT=http://localhost:8098 # Or your deployed Supabase MCP endpoint
TRIPSAGE_MCP_SUPABASE_API_KEY=your_supabase_mcp_api_key
TRIPSAGE_MCP_SUPABASE_DEFAULT_PROJECT_ID=your_supabase_project_id
TRIPSAGE_MCP_SUPABASE_DEFAULT_ORGANIZATION_ID=your_supabase_organization_id
# ENVIRONMENT=production or staging
````

**For Neon MCP (Development Environment MCP Interaction):**

```plaintext
# .env example for Neon MCP
TRIPSAGE_MCP_NEON_ENDPOINT=http://localhost:8099 # Or your deployed Neon MCP endpoint
TRIPSAGE_MCP_NEON_API_KEY=your_neon_mcp_api_key
TRIPSAGE_MCP_NEON_DEFAULT_PROJECT_ID=your_neon_project_id
# ENVIRONMENT=development or testing
```

The `NEXT_PUBLIC_` prefix is used in frontend projects (like Next.js) to make variables available to client-side code. Backend services should access these without the prefix.

## 3. Database Schema and Migrations

TripSage uses a carefully designed relational schema to support its travel planning functionalities.

### 3.1 Schema Naming Conventions

- Use `snake_case` for all table and column names.
- Tables are lowercase with underscores separating words.
- Foreign keys use the singular form of the referenced table with an `_id` suffix (e.g., `trip_id` in the `flights` table referencing `trips.id`).
- Include `created_at` and `updated_at` (TIMESTAMPTZ) columns on all relevant tables, typically with `DEFAULT now()`.
- Add comments to tables and complex columns for clarity.

### 3.2 Core Tables

(Refer to `docs/08_REFERENCE/Database_Schema_Details.md` for the complete and detailed schema of all tables like `users`, `trips`, `flights`, `accommodations`, `transportation`, `itinerary_items`, etc.)

**Example: `trips` table**

```sql
CREATE TABLE trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL, -- Assuming Supabase Auth users
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT NOT NULL,
    budget NUMERIC NOT NULL,
    travelers INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'planning', -- e.g., 'planning', 'booked', 'completed', 'canceled'
    trip_type TEXT NOT NULL DEFAULT 'leisure', -- e.g., 'leisure', 'business', 'family', 'solo'
    flexibility JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT trips_date_check CHECK (end_date >= start_date),
    CONSTRAINT trips_travelers_check CHECK (travelers > 0),
    CONSTRAINT trips_budget_check CHECK (budget >= 0),
    CONSTRAINT trips_status_check CHECK (status IN ('planning', 'booked', 'completed', 'canceled')),
    CONSTRAINT trips_type_check CHECK (trip_type IN ('leisure', 'business', 'family', 'solo', 'other'))
);

COMMENT ON TABLE trips IS 'Stores primary information about user-planned trips.';
COMMENT ON COLUMN trips.flexibility IS 'JSONB field for storing flexibility preferences, e.g., date ranges, budget flexibility.';
```

### 3.3 Migration Management

- **Migration Scripts**: SQL migration scripts are located in the `/migrations` directory (or a similar designated path). They follow a naming convention like `YYYYMMDDHHMMSS_description.sql`.
- **Applying Migrations**:
  - **Supabase**: Migrations can be applied via the Supabase Dashboard (SQL Editor) or using a PostgreSQL client (like `psql`) connected to the Supabase instance. For CI/CD, the Supabase CLI or database MCP tools are used.
  - **Neon**: Migrations are applied to specific branches, often using `psql` or a database migration tool integrated into the development workflow.
- **Migration Tools**: Consider using tools like `Alembic` (for Python projects) or the Supabase CLI's built-in migration features for managing and applying migrations systematically.
- **Order of Execution**: Ensure migration scripts are applied in the correct chronological order.
- **Idempotency**: Design migration scripts to be idempotent where possible (e.g., using `IF NOT EXISTS` for creating objects, `IF EXISTS` for dropping).
- **Rollbacks**: For critical migrations, prepare corresponding rollback scripts.

**Example Migration Application (Manual via psql):**

```bash
# Connect to your database (replace with your actual connection string)
# For Supabase:
# PGPASSWORD="[YOUR_DB_PASSWORD]" psql -h db.[PROJECT_REF].supabase.co -p 5432 -U postgres -d postgres
# For Neon:
# psql "postgresql://[USER]:[PASSWORD]@[ENDPOINT_HOST]/[DB_NAME]?sslmode=require"

# Navigate to migrations directory
cd migrations

# Run migration files in order
psql -f YYYYMMDDHHMMSS_initial_schema.sql
psql -f YYYYMMDDHHMMSS_add_new_feature_table.sql
# ... and so on
```

### 3.4 Seeding Data

- Initial seed data for development and testing can be managed via SQL scripts or programmatic seeding using the MCP clients.
- Supabase provides a `supabase db seed` command if using its local development setup.

## 4. TypeScript Integration (Frontend & Node.js Services)

For projects using TypeScript (like the Next.js frontend), Supabase provides type generation from the database schema.

### 4.1 Type Definitions

Type definitions are typically stored in a file like `src/types/supabase.ts`.

```typescript
// Example: src/types/supabase.ts
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          /* ... fields ... */
        };
        Insert: {
          /* ... fields ... */
        };
        Update: {
          /* ... fields ... */
        };
        Relationships: [];
      };
      trips: {
        Row: {
          id: number;
          user_id: string;
          name: string;
          start_date: string;
          end_date: string;
          destination: string;
          budget: number;
          travelers: number;
          status: string;
          trip_type: string;
          flexibility: Json | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          /* ... similar fields, some optional or excluded (like id, created_at) ... */
        };
        Update: {
          /* ... similar fields, all optional ... */
        };
        Relationships: [
          {
            foreignKeyName: "trips_user_id_fkey";
            columns: ["user_id"];
            referencedRelation: "users"; // Supabase auth users table
            referencedColumns: ["id"];
          }
        ];
      };
      // ... other table definitions
    };
    Views: {
      /* ... view definitions ... */
    };
    Functions: {
      /* ... function definitions ... */
    };
    Enums: {
      /* ... enum definitions ... */
    };
    CompositeTypes: {
      /* ... composite type definitions ... */
    };
  };
}

// Type aliases for easier usage
export type User = Database["public"]["Tables"]["users"]["Row"];
export type Trip = Database["public"]["Tables"]["trips"]["Row"];
// ... other type aliases
```

### 4.2 Type Generation

Use the Supabase CLI to generate types automatically from your live database schema:

```bash
supabase gen types typescript --project-id your-project-id > src/types/supabase.ts
# Or for a local Supabase instance:
# supabase gen types typescript --local > src/types/supabase.ts
```

This command should be run whenever the database schema changes to keep TypeScript types synchronized.

## 5. MCP Integration for Database Operations

TripSage standardizes database interactions through an MCP (Model Context Protocol) layer. This involves specialized MCP clients for Neon (development) and Supabase (production).

### 5.1 Key MCP Components

- **`NeonMCPClient`**: For development environments.
  - Manages Neon-specific features like project and branch operations.
  - Provides SQL execution and transaction support.
- **`SupabaseMCPClient`**: For production/staging environments.
  - Manages Supabase project operations.
  - Handles SQL execution, RLS management, and TypeScript type generation.
- **`DatabaseMCPFactory`**: A factory that selects the appropriate client (`NeonMCPClient` or `SupabaseMCPClient`) based on the current `ENVIRONMENT` setting.

### 5.2 Environment Selection Logic

The factory pattern determines which client to use:

````python
# From src/mcp/db_factory.py (Conceptual)
# Actual implementation might vary based on final structure

# from src.utils.settings import settings, Environment
# from src.mcp.neon.client import NeonMCPClient, get_neon_client # Assuming these exist
# from src.mcp.supabase.client import SupabaseMCPClient, get_supabase_client # Assuming these exist

# def get_database_mcp_client(environment: Optional[str] = None) -> Union[NeonMCPClient, SupabaseMCPClient]:
#     """Get the appropriate database MCP client based on the environment."""
#     active_environment = environment or settings.ENVIRONMENT

#     if active_environment.lower() in [Environment.DEVELOPMENT.value, Environment.TESTING.value]:
#         logger.info(f"Using NeonMCPClient for {active_environment} environment")
#         return get_neon_client() # Factory function for Neon client
#     else: # Production, Staging, etc.
#         logger.info(f"Using SupabaseMCPClient for {active_environment} environment")
#         return get_supabase_client() # Factory function for Supabase client```

### 5.3 Configuration for Database MCPs

Configuration for these MCPs is managed via the centralized `AppSettings` and environment variables.

**`NeonMCPConfig` (Example from `settings.py`):**
```python
# class NeonMCPConfig(MCPConfig): # Assuming MCPConfig is a base Pydantic model
#     dev_only: bool = Field(default=True)
#     default_project_id: Optional[str] = None
#     # ... other Neon specific settings
````

**`SupabaseMCPConfig` (Example from `settings.py`):**

```python
# class SupabaseMCPConfig(MCPConfig):
#     prod_only: bool = Field(default=True)
#     default_project_id: Optional[str] = None
#     default_organization_id: Optional[str] = None
#     # ... other Supabase specific settings
```

### 5.4 Common Operations via MCP

- **Creating Development Branches (Neon)**:
  The `NeonService` (built on `NeonMCPClient`) can create isolated database branches for feature development.

  ```python
  # Conceptual usage
  # neon_service = DatabaseMCPFactory.get_development_service()
  # branch_info = await neon_service.create_development_branch(branch_name=f"db-{git_branch_name}")
  # connection_string = branch_info["connection_string"]
  # # Update .env.local or similar with this connection string for the feature branch
  ```

- **Applying Migrations (Supabase/Neon)**:
  Both `SupabaseService` and `NeonService` provide methods to apply SQL migration files.

  ```python
  # Conceptual usage for production
  # supabase_service = DatabaseMCPFactory.get_production_service()
  # migration_files_content = [...] # Read from /migrations
  # migration_names = [...]
  # result = await supabase_service.apply_migrations(
  #     project_id=settings.supabase_mcp.default_project_id,
  #     migrations=migration_files_content,
  #     migration_names=migration_names
  # )
  ```

- **Executing SQL**:
  Both clients offer an `execute_sql` tool for running arbitrary SQL queries, which is useful for custom data retrieval or modifications not covered by standard ORM-like methods.

### 5.5 External MCP Server Integration

TripSage integrates with official or community-maintained MCP server packages for Supabase (`supabase-mcp`) and Neon (`mcp-server-neon`) as external dependencies rather than implementing custom MCP servers for these databases. This strategy offers:

- **Standardization**: Compliance with MCP specifications.
- **Reduced Maintenance**: Delegates server upkeep to dedicated packages.
- **Up-to-Date Functionality**: Benefits from updates and features in the official implementations.

## 6. Frontend Integration (Next.js with Supabase Client)

The Next.js frontend interacts with Supabase primarily for authentication and real-time features, and sometimes for direct data fetching (though most data access should go through the FastAPI backend).

### 6.1 Client Setup

Two types of Supabase clients are used in the frontend:

1. **Server-Side Client (`lib/supabase/server.ts`)**: For use in Server Components, API routes, and server-side data fetching functions. It uses `@supabase/ssr`.

    ```typescript
    // lib/supabase/server.ts
    import { createServerClient, type CookieOptions } from "@supabase/ssr";
    import { cookies } from "next/headers";
    import { Database } from "@/types_db"; // Assuming types_db.ts from supabase gen types

    export function createSupabaseServerClient() {
      const cookieStore = cookies();
      return createServerClient<Database>(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
          cookies: {
            get(name: string) {
              return cookieStore.get(name)?.value;
            },
            set(name: string, value: string, options: CookieOptions) {
              cookieStore.set({ name, value, ...options });
            },
            remove(name: string, options: CookieOptions) {
              cookieStore.set({ name, value: "", ...options });
            },
          },
        }
      );
    }
    ```

2. **Client-Side Client (`lib/supabase/client.ts`)**: For use in Client Components (hooks, event handlers). It uses `@supabase/auth-helpers-nextjs`.

    ```typescript
    // lib/supabase/client.ts
    "use client";
    import { createBrowserClient } from "@supabase/ssr";
    import { Database } from "@/types_db"; // Assuming types_db.ts

    export function createSupabaseBrowserClient() {
      return createBrowserClient<Database>(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
      );
    }
    ```

### 6.2 Authentication Integration

Supabase Auth is integrated using middleware for session management and protecting routes.

```typescript
// middleware.ts
import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { Database } from "@/types_db";

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return req.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          res.cookies.set({ name, value, ...options });
        },
        remove(name: string, options: CookieOptions) {
          res.cookies.set({ name, value: "", ...options });
        },
      },
    }
  );

  const {
    data: { session },
  } = await supabase.auth.getSession();

  // Example: Redirect to login if accessing protected /app routes without a session
  if (!session && req.nextUrl.pathname.startsWith("/app")) {
    return NextResponse.redirect(new URL("/auth/login", req.url));
  }

  return res;
}

export const config = {
  matcher: ["/app/:path*", "/api/protected/:path*"], // Define routes to be covered by middleware
};
```

### 6.3 Real-time Features

Supabase's real-time capabilities are leveraged for features like collaborative trip planning or live updates.

```typescript
// Example: hooks/useTripUpdates.ts (Client Component)
"use client";
import { useEffect, useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { Trip } from "@/types_db"; // Assuming Trip type from generated types

export function useTripUpdates(tripId: string) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const supabase = createSupabaseBrowserClient();

  useEffect(() => {
    if (!tripId) return;

    const channel = supabase
      .channel(`trip-updates-${tripId}`)
      .on<Trip>(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "trips",
          filter: `id=eq.${tripId}`,
        },
        (payload) => {
          setTrip(payload.new as Trip);
        }
      )
      .subscribe();

    // Fetch initial trip data
    const fetchInitialTrip = async () => {
      const { data, error } = await supabase
        .from("trips")
        .select("*")
        .eq("id", tripId)
        .single();
      if (error) console.error("Error fetching initial trip:", error);
      else setTrip(data);
    };
    fetchInitialTrip();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [tripId, supabase]);

  return trip;
}
```

## 7. Security Implementation

### 7.1 Row-Level Security (RLS)

RLS is extensively used in Supabase to protect user data.

- Enable RLS on all tables containing user-specific or sensitive data.
- Define policies to ensure users can only access and modify their own data.

**Example RLS Policies:**

```sql
-- Enable RLS on the 'trips' table
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;

-- Policy: Users can select their own trips
CREATE POLICY "Users can select their own trips"
ON trips FOR SELECT
USING (auth.uid() = user_id); -- Assumes user_id in trips table matches auth.uid()

-- Policy: Users can insert new trips for themselves
CREATE POLICY "Users can insert their own trips"
ON trips FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own trips
CREATE POLICY "Users can update their own trips"
ON trips FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own trips
CREATE POLICY "Users can delete their own trips"
ON trips FOR DELETE
USING (auth.uid() = user_id);
```

(Note: The `user_id` column in your tables should correspond to `auth.uid()` from Supabase's authentication system.)

### 7.2 API Key Management

- **Public Anon Key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`)**: Used for client-side operations with RLS enforcement. Limited permissions.
- **Service Role Key (`SUPABASE_SERVICE_ROLE_KEY`)**: Used only in trusted server environments (like the FastAPI backend or serverless functions) for operations that need to bypass RLS (e.g., administrative tasks, backend processing). **This key must be kept secret.**
- **Key Rotation**: Implement a policy for regular rotation of the service role key, managed through CI/CD pipelines or secure secret management systems.

## 8. Performance Optimization

### 8.1 Indexing Strategy

A comprehensive indexing strategy is crucial for query performance.

```sql
-- Example indexes for the 'trips' table
-- Index on user_id for fast retrieval of a user's trips
CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips(user_id);

-- Index on destination for searching trips by destination
CREATE INDEX IF NOT EXISTS idx_trips_destination ON trips USING gin (to_tsvector('english', destination)); -- For text search
-- OR for exact matches: CREATE INDEX IF NOT EXISTS idx_trips_destination_exact ON trips(destination);


-- Index on dates for filtering by date ranges
CREATE INDEX IF NOT EXISTS idx_trips_dates ON trips (start_date, end_date);

-- Example indexes for 'flights' table
CREATE INDEX IF NOT EXISTS idx_flights_trip_id ON flights(trip_id);
CREATE INDEX IF NOT EXISTS idx_flights_origin_destination ON flights (origin, destination);
CREATE INDEX IF NOT EXISTS idx_flights_departure_time ON flights (departure_time);
```

(Refer to `docs/08_REFERENCE/Database_Schema_Details.md` for more specific index examples if available, or ensure they are defined in migration scripts.)

### 8.2 Query Optimization

- **Select Specific Columns**: Avoid `SELECT *` where possible; fetch only the columns needed.
- **Use Pagination**: Implement `LIMIT` and `OFFSET` for queries that might return many results.
- **Efficient Joins**: Utilize Supabase's relationship expansion features in client libraries or write efficient SQL JOINs.

  ```typescript
  // Example of optimized query with relationship expansion in Supabase JS client
  // const { data: tripsWithFlights } = await supabase
  //   .from("trips")
  //   .select(`
  //     id,
  //     name,
  //     destination,
  //     flights (id, airline, departure_time)
  //   `)
  //   .eq("user_id", userId)
  //   .order("start_date", { ascending: true })
  //   .range(0, 9); // Pagination for first 10 results
  ```

### 8.3 Caching Strategy (Database Layer)

- **Client-Side Caching (Frontend)**: Use libraries like React Query (`@tanstack/react-query`) for caching data fetched by the frontend, managing stale data, and background updates.

  ```typescript
  // Example: hooks/useTripsData.ts (Client Component)
  // import { useQuery } from "@tanstack/react-query";
  // import { createSupabaseBrowserClient } from "@/lib/supabase/client";

  // export function useUserTrips(userId: string) {
  //   const supabase = createSupabaseBrowserClient();
  //   return useQuery({
  //     queryKey: ["userTrips", userId],
  //     queryFn: async () => {
  //       const { data, error } = await supabase
  //         .from("trips")
  //         .select("*")
  //         .eq("user_id", userId)
  //         .order("created_at", { ascending: false });
  //       if (error) throw error;
  //       return data;
  //     },
  //     staleTime: 60 * 1000, // 1 minute
  //     enabled: !!userId, // Only run query if userId is available
  //   });
  // }
  ```

- **Backend Caching**: The FastAPI backend can implement caching (e.g., using Redis) for frequently accessed data that doesn't change often, reducing database load.
- **Database Query Cache**: PostgreSQL itself has internal caching mechanisms. Ensure your queries are written to take advantage of these (e.g., using prepared statements, avoiding volatile functions in indexed expressions).

## 9. Testing Strategy for Database Interactions

- **Local Development (Neon)**: Use Neon's branching to create isolated databases for testing new features or migrations without affecting other developers or a shared dev database.
- **Mocking (Unit Tests)**:
  - For unit tests of services that interact with the database (via MCP clients or direct clients), mock the database client methods.
  - Example using `pytest` and `unittest.mock`:

    ```python
    # from unittest.mock import AsyncMock, patch
    # @patch('your_project.db_client_module.supabase_mcp_client.execute_sql', new_callable=AsyncMock)
    # async def test_some_service_method(mock_execute_sql):
    #     mock_execute_sql.return_value = {"data": [{"id": 1, "name": "Test Trip"}], "error": None}
    #     # ... call your service method that uses execute_sql ...
    #     # ... assert results ...
    #     mock_execute_sql.assert_called_once_with(...)
    ```

- **Integration Tests**:
  - Run integration tests against a dedicated test database (a Neon branch or a separate Supabase project).
  - These tests verify actual database interactions, RLS policies, and data integrity.
- **End-to-End (E2E) Tests**: Use tools like Playwright to test user flows that involve database operations through the entire stack (frontend -> backend -> database).

## 10. Best Practices for Supabase and Neon

- **Environment Awareness**: Always be clear about which environment (Neon dev branch, Supabase staging, Supabase prod) you are targeting.
- **Connection Pooling**:
  - Supabase manages connection pooling. Be mindful of connection limits on your plan.
  - For backend services connecting directly, use a robust connection pooler like PgBouncer if not using Supabase's built-in pooling effectively. Neon also benefits from connection pooling.
- **Security**:
  - Regularly review RLS policies in Supabase.
  - Keep API keys and database credentials secure.
  - Use Supabase's built-in Auth for user management.
- **Neon Branch Management**:
  - Adopt a strategy for naming and cleaning up Neon branches (e.g., `feature/[issue-id]`, delete after merge).
  - Leverage Neon's "Time Travel" (Point-in-Time Recovery) for debugging or restoring data on development branches.

This guide provides a comprehensive overview of using relational databases within the TripSage ecosystem, ensuring a robust, secure, and performant data layer for the application.
