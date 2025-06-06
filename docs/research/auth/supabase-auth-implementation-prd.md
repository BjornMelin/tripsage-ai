# Supabase Auth Implementation PRD

> **Document Version**: 2.0  
> **Created**: June 2025  
> **Status**: Ready for Implementation  
> **Project**: TripSage AI Authentication System

## Product Requirements Document

### 1. Overview

This PRD outlines the implementation plan for integrating Supabase Auth as the primary authentication system for TripSage. Since the application has no existing users and the custom JWT implementation was never deployed, we can implement Supabase Auth as a greenfield solution without any migration concerns.

### 2. Objectives

#### Primary Objectives

1. **Security First**: Implement enterprise-grade authentication from day one
2. **Zero Maintenance**: Use managed service to eliminate authentication maintenance
3. **Advanced Features**: Enable MFA, OAuth, magic links, and session management
4. **Scalable Foundation**: Build authentication that scales from 0 to millions of users

#### Success Criteria

- ✅ Zero authentication-related security vulnerabilities
- ✅ Clean, minimal authentication codebase
- ✅ <100ms authentication latency
- ✅ OAuth provider integration (Google, GitHub)
- ✅ Complete test coverage for auth flows

### 3. Scope

#### In Scope

- Supabase Auth integration for Next.js frontend
- FastAPI backend token validation
- OAuth provider setup (Google, GitHub)
- Email/password authentication
- Session management and refresh tokens
- Row Level Security (RLS) implementation
- Removal of custom JWT code
- Documentation and testing

#### Out of Scope

- SMS authentication (Phase 2)
- Advanced MFA implementations (Phase 2)
- SAML/Enterprise SSO (Future)
- Custom authentication UI (using Supabase components)

### 4. User Stories

#### As a User

1. **I want to** create an account easily **so that** I can start planning trips
2. **I want to** use Google/GitHub login **so that** I don't need to remember another password
3. **I want to** stay logged in **so that** I don't need to authenticate repeatedly
4. **I want to** reset my password securely **so that** I can recover my account

#### As a Developer

1. **I want to** validate tokens easily **so that** I can secure API endpoints
2. **I want to** manage user sessions **so that** I can track active users
3. **I want to** implement RLS **so that** users only see their own data
4. **I want to** monitor auth events **so that** I can detect security issues

### 5. Technical Requirements

#### Frontend Requirements

- Next.js 15.3.2 compatibility
- React 19 Server Components support
- TypeScript type safety
- Cookie-based session management
- PKCE flow for OAuth

#### Backend Requirements

- FastAPI token validation
- Supabase Python client integration
- JWT verification without secret management
- Request authentication middleware
- User context injection

#### Database Requirements

- Enable RLS on all user tables
- Auth schema integration
- User ID foreign key relationships
- Migration scripts for existing users
- Audit logging tables

### 6. Architecture

#### System Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (Next.js 15)"]
        A1["App Dir Routes"] --- A2["Middleware Auth"] --- A3["@supabase/ssr Client"]
    end
    
    subgraph Supabase["Supabase Cloud"]
        B1["Auth Service"] --- B2["Database PostgreSQL"] --- B3["Realtime Websocket"]
    end
    
    subgraph Backend["Backend (FastAPI)"]
        C1["Routes API"] --- C2["Auth Dependency"] --- C3["Business Services"]
    end
    
    Frontend ---|HTTPS| Supabase
    Supabase ---|JWT Validation| Backend
    
    style Frontend fill:#1e3a8a,stroke:#3b82f6,color:#ffffff
    style Supabase fill:#064e3b,stroke:#10b981,color:#ffffff
    style Backend fill:#7c2d12,stroke:#f97316,color:#ffffff
```

#### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Next.js Frontend
    participant S as Supabase Auth
    participant M as Next.js Middleware
    participant B as FastAPI Backend
    
    Note over U,B: 1. User Login Request
    U->>F: Login Request
    F->>S: Authenticate User
    S->>S: Validate Credentials
    S->>S: Generate JWT + Refresh Token
    S->>F: Set Secure Cookies
    F->>U: Return User Session
    
    Note over U,B: 2. API Request
    U->>F: API Request
    F->>M: Validate Session Cookie
    M->>F: Forward to API Route
    F->>B: API Call with JWT
    B->>B: Validate Supabase JWT
    B->>B: Execute Business Logic
    B->>F: Return Response
    F->>U: Return Data
    
    Note over U,B: 3. Token Refresh (Automatic)
    F->>S: Check Token Expiration
    S->>S: Exchange Refresh Token
    S->>F: New Access Token
    F->>F: Update Cookies
```

### 7. Implementation Plan

#### Pre-Implementation Tasks

- [ ] **Fix Pydantic v1→v2 Migration** (Blocking - 1-2 days)
- [ ] **Create Dashboard Page** (Critical - 2 hours)
- [x] **Remove Custom JWT Code** ✅ (Completed June 6, 2025)
  - [x] Deleted `frontend/src/lib/auth/server-actions.ts`
  - [x] Reverted JWT-related code from `frontend/src/middleware.ts`
  - [x] Removed `AuthenticationService` from backend
  - [x] Reverted multiple files to pre-JWT state using git
  - [x] Removed JWT dependencies from package.json and pyproject.toml
  - [x] Deleted all JWT-related test files

#### Phase 1: Setup & Configuration (Day 1)

##### 1.1 Supabase Project Configuration

```bash
# No new project needed - use existing Supabase instance
# Enable Auth in Supabase Dashboard
```

**Tasks:**

- [ ] Enable Authentication in Supabase dashboard
- [ ] Configure JWT secret for FastAPI validation
- [ ] Set up email templates for auth emails
- [ ] Configure OAuth providers (Google, GitHub)
- [ ] Set session timeout parameters
- [ ] Enable email verification requirement

##### 1.2 Environment Configuration

```bash
# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[anon_key]

# Backend (.env)
SUPABASE_URL=https://[project].supabase.co
SUPABASE_SERVICE_KEY=[service_key]
SUPABASE_JWT_SECRET=[jwt_secret]
```

**Tasks:**

- [ ] Add Supabase Auth environment variables
- [ ] Remove all JWT_SECRET related variables
- [ ] Update deployment configurations
- [ ] Document environment changes in `.env.example`

#### Phase 2: Frontend Implementation (Day 2)

##### 2.1 Install Dependencies

```bash
cd frontend
pnpm add @supabase/supabase-js @supabase/ssr
pnpm remove jose bcryptjs  # Remove custom JWT dependencies
```

##### 2.2 Create Supabase Client Utilities

```typescript
// src/lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}

// src/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()
  
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

##### 2.3 Update Authentication Actions

```typescript
// src/lib/auth/supabase-actions.ts
'use server'

import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export async function signIn(email: string, password: string) {
  const supabase = await createClient()
  
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })
  
  if (error) {
    return { error: error.message }
  }
  
  redirect('/dashboard')
}

export async function signUp(email: string, password: string, name: string) {
  const supabase = await createClient()
  
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { name }
    }
  })
  
  if (error) {
    return { error: error.message }
  }
  
  return { data }
}

export async function signOut() {
  const supabase = await createClient()
  await supabase.auth.signOut()
  redirect('/login')
}
```

##### 2.4 Update Middleware

```typescript
// src/middleware.ts
import { createServerClient } from '@supabase/ssr'
import { type NextRequest, NextResponse } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  // Protected routes
  if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Auth routes redirect if logged in
  if (user && ['/login', '/register'].includes(request.nextUrl.pathname)) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}
```

**Tasks:**

- [ ] Create Supabase client utilities
- [ ] Create new Supabase auth actions
- [ ] Replace middleware with Supabase implementation
- [ ] Update auth forms to use new actions
- [ ] Delete all custom JWT code
- [ ] Test all auth flows

#### Phase 3: Backend Integration (Day 2-3)

##### 3.1 Install Backend Dependencies

```bash
cd tripsage
uv pip install supabase
```

##### 3.2 Create Supabase Auth Dependency

```python
# tripsage_core/dependencies/auth.py
from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from jose import jwt, JWTError

from tripsage_core.config import get_settings

security = HTTPBearer()
settings = get_settings()

def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key
    )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> dict:
    """Validate Supabase JWT and return user."""
    token = credentials.credentials
    
    try:
        # Decode JWT using Supabase JWT secret
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Get user from Supabase
        user = supabase.auth.admin.get_user_by_id(payload['sub'])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        return user.user
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
```

##### 3.3 Update API Routes

```python
# tripsage/api/routers/trips.py
from fastapi import APIRouter, Depends
from tripsage_core.dependencies.auth import get_current_user

router = APIRouter()

@router.get("/trips")
async def get_user_trips(user: dict = Depends(get_current_user)):
    """Get trips for authenticated user."""
    user_id = user['id']
    # Fetch user trips
    return {"trips": [], "user_id": user_id}
```

**Tasks:**

- [ ] Install supabase Python package
- [ ] Create auth dependency
- [ ] Update all protected routes
- [ ] Delete AuthenticationService and related code
- [ ] Test API authentication
- [ ] Update API documentation

#### Phase 4: Database Security (Day 3)

##### 4.1 Enable Row Level Security

```sql
-- Enable RLS on all user tables
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE accommodations ENABLE ROW LEVEL SECURITY;
ALTER TABLE flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE itinerary_items ENABLE ROW LEVEL SECURITY;

-- Create policies for trips
CREATE POLICY "Users can view own trips" ON trips
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own trips" ON trips
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own trips" ON trips
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own trips" ON trips
    FOR DELETE USING (auth.uid() = user_id);

-- Repeat for other tables...
```

##### 4.2 Database Setup

Since we have no existing users, we simply need to ensure our database schema is ready for Supabase Auth:

```sql
-- Ensure users table uses Supabase auth.users ID
ALTER TABLE users 
  ADD CONSTRAINT users_id_fkey 
  FOREIGN KEY (id) 
  REFERENCES auth.users(id) 
  ON DELETE CASCADE;

-- Create trigger to auto-create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, email, name, created_at)
  VALUES (
    new.id,
    new.email,
    new.raw_user_meta_data->>'name',
    now()
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

**Tasks:**

- [ ] Create RLS policies for all tables
- [ ] Set up database triggers for new user creation
- [ ] Verify foreign key constraints
- [ ] Test database security

#### Phase 5: Testing & Deployment (Day 3)

##### 5.1 Test Coverage

- [ ] Unit tests for auth utilities
- [ ] Integration tests for auth flows
- [ ] E2E tests for user journeys
- [ ] Security tests for RLS policies
- [ ] Performance tests for auth latency

##### 5.2 Deployment Checklist

- [ ] Update environment variables
- [ ] Deploy frontend changes
- [ ] Deploy backend changes
- [ ] Run database migrations
- [ ] Enable RLS policies
- [ ] Monitor for errors
- [ ] Rollback plan ready

### 8. Rollback Plan

Since we have no existing users, rollback is simplified:

1. **Code Rollback**
   - Revert Git commits to pre-Supabase state
   - Or redeploy previous version

2. **Database Rollback**
   - Disable RLS policies
   - Drop auth triggers
   - Clear any test user data

3. **Environment Rollback**
   - Restore previous environment variables
   - Disable Supabase Auth in dashboard

### 9. Success Metrics

#### Technical Metrics

- Authentication latency: <100ms (p95)
- Token refresh success rate: >99.9%
- Zero authentication errors in production
- 90% reduction in auth-related code

#### Business Metrics

- User login success rate: >95%
- Password reset completion: >80%
- OAuth adoption rate: >30% in 30 days
- Zero security incidents

#### Monitoring & Alerts

- Supabase Auth dashboard metrics
- Custom auth event logging
- Error rate monitoring
- Latency tracking

### 10. Future Enhancements

#### Phase 2 (Q3 2025)

- [ ] SMS/Phone authentication
- [ ] Advanced MFA (TOTP apps)
- [ ] Social login expansion
- [ ] Session management UI

#### Phase 3 (Q4 2025)

- [ ] Enterprise SSO (SAML)
- [ ] Advanced audit logging
- [ ] Compliance certifications
- [ ] Custom auth UI components

### 11. Task Summary

#### Critical Path (Must Complete First)

1. Fix Pydantic v1→v2 migration (1-2 days)
2. Create dashboard page (2 hours)
3. ~~Remove custom JWT code~~ ✅ **COMPLETED** (June 6, 2025)

#### Implementation Tasks (Sequential)

1. **Day 1**: ~~Remove JWT code~~ ✅ & Supabase configuration
2. **Day 2**: Frontend & backend implementation
3. **Day 3**: Database security, testing & deployment

#### Total Effort

- **Development**: 20 hours (2.5 days)
- **Testing**: 6 hours
- **Deployment**: 2 hours
- **Total**: 28 hours over 2-3 days

### 12. Clean Code Approach

Since we're implementing fresh with no users:

1. **Delete all custom JWT code** ✅ **COMPLETED** (June 6, 2025):
   - [x] Deleted `frontend/src/lib/auth/server-actions.ts`
   - [x] Reverted JWT logic in `frontend/src/middleware.ts` to pre-JWT state
   - [x] Deleted `tripsage_core/services/business/auth_service.py`
   - [x] Removed JWT configuration from settings
   - [x] Removed JWT dependencies from package.json and pyproject.toml
   - [x] Deleted all JWT-related test files

2. **Start fresh with Supabase**:
   - No backwards compatibility needed
   - No migration scripts required
   - Clean, minimal implementation

3. **Version Control Approach Used**:
   - ✅ Used git log to identify JWT implementation commits
   - ✅ Reverted files to pre-JWT state using git checkout
   - ✅ Deleted JWT-specific files entirely
   - ✅ Project now in clean state ready for Supabase Auth

### 13. References

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Next.js App Router Auth Guide](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [FastAPI Integration Examples](https://github.com/supabase-community/supabase-py)
- [Row Level Security Guide](https://supabase.com/docs/guides/database/postgres/row-level-security)

---

*This PRD is a living document and will be updated throughout the implementation process.*
