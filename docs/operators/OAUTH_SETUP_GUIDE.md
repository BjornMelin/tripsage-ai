# OAuth Provider Setup Guide

This comprehensive guide walks you through setting up OAuth providers for TripSage authentication with detailed step-by-step instructions, security best practices, and troubleshooting guidance.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google OAuth Setup](#google-oauth-setup)
3. [GitHub OAuth Setup](#github-oauth-setup)
4. [Configuration Management](#configuration-management)
5. [Security Best Practices](#security-best-practices)
6. [Testing and Validation](#testing-and-validation)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

## Prerequisites

**Required Access:**
- ✅ Supabase project with authentication enabled
- ✅ Google Cloud Console account with admin permissions
- ✅ GitHub account with developer access
- ✅ Admin access to your Supabase dashboard
- ✅ Domain ownership (for production setup)

**Technical Requirements:**
- ✅ HTTPS-enabled domain for production
- ✅ Valid SSL certificate
- ✅ TripSage frontend deployed and accessible
- ✅ Environment variable management system

**Supported Providers:**
- ✅ Google OAuth 2.0 (Recommended)
- ✅ GitHub OAuth (Recommended)
- 🔄 Facebook OAuth (Available)
- 🔄 Microsoft OAuth (Available)
- 🔄 Apple Sign-In (Enterprise)

---

## Google OAuth Setup

### Overview

Google OAuth 2.0 integration allows users to sign in using their Google accounts. This section provides comprehensive setup instructions for both development and production environments.

### Step 1: Google Cloud Console Project Setup

#### 1.1 Create or Select Project

1. **Navigate** to [Google Cloud Console](https://console.cloud.google.com/)
2. **Click** the project dropdown at the top of the page
3. **Choose** one of the following:
   - **Existing Project**: Select "TripSage" if it already exists
   - **New Project**: Click "New Project"

**For New Project:**
```
Project Name: TripSage
Project ID: tripsage-[random-id] (auto-generated)
Organization: [Your Organization] (optional)
Location: [Your Organization] (optional)
```

4. **Click** "Create" and wait for project creation
5. **Verify** project selection in the top navigation bar

#### 1.2 Enable Required APIs

1. **Navigate** to **APIs & Services** → **Library**
2. **Search** for "Google+ API"
3. **Click** on "Google+ API" (or "People API" for newer setups)
4. **Click** "Enable"
5. **Wait** for API activation (usually 1-2 minutes)

**Alternative APIs (Recommended for new projects):**
- **Google Identity API** (preferred)
- **People API** (for profile data)

### Step 2: OAuth Consent Screen Configuration

#### 2.1 Basic Setup

1. **Navigate** to **APIs & Services** → **OAuth consent screen**
2. **Select** user type:
   - **Internal**: If using Google Workspace (recommended for organizations)
   - **External**: For public applications (recommended for TripSage)

3. **Click** "Create"

#### 2.2 OAuth Consent Screen Details

**App Information:**
```
App name: TripSage
User support email: support@your-domain.com
App logo: [Upload TripSage logo - 120x120px PNG]
```

**App Domain Information:**
```
Application home page: https://your-domain.com
Application privacy policy link: https://your-domain.com/privacy
Application terms of service link: https://your-domain.com/terms
```

**Authorized Domains:**
```
your-domain.com
[your-domain].vercel.app (if using Vercel)
localhost (for development)
```

**Developer Contact Information:**
```
Email addresses: 
- developer@your-domain.com
- admin@your-domain.com
```

4. **Click** "Save and Continue"

#### 2.3 Scopes Configuration

1. **Click** "Add or Remove Scopes"
2. **Select** the following scopes:
   ```
   ../auth/userinfo.email    (Required)
   ../auth/userinfo.profile  (Required)
   openid                    (Required)
   ```

3. **Click** "Update"
4. **Click** "Save and Continue"

#### 2.4 Test Users (External Apps Only)

For development and testing with external user type:
1. **Add** test user emails:
   ```
   developer@your-domain.com
   tester@your-domain.com
   your-personal@gmail.com
   ```

2. **Click** "Save and Continue"

### Step 3: OAuth 2.0 Credentials Creation

#### 3.1 Create Web Application Credentials

1. **Navigate** to **APIs & Services** → **Credentials**
2. **Click** "Create Credentials" → "OAuth 2.0 Client ID"
3. **Select** "Web application"

#### 3.2 Configure Application Details

**Application Details:**
```
Name: TripSage Web Client
```

**Authorized JavaScript Origins:**
```
https://your-domain.com
https://www.[your-domain].com
http://localhost:3000 (development)
http://localhost:3001 (development backup)
```

**Authorized Redirect URIs:**
```
https://[project-ref].supabase.co/auth/v1/callback
https://your-domain.com/auth/callback
http://localhost:3000/auth/callback (development)
```

**To find your Supabase project reference:**
1. Go to your Supabase dashboard
2. Select your project
3. Go to Settings → API
4. Copy the "Reference ID"

4. **Click** "Create"

#### 3.3 Save Credentials

1. **Copy** the generated credentials:
   ```
   Client ID: [long-string].apps.googleusercontent.com
   Client Secret: [secret-string]
   ```

2. **Download** JSON file for backup
3. **Store** credentials securely (never commit to version control)

### Step 4: Supabase Configuration

#### 4.1 Enable Google Provider

1. **Open** Supabase Dashboard
2. **Navigate** to your TripSage project
3. **Go** to **Authentication** → **Providers**
4. **Locate** "Google" provider
5. **Toggle** the enable switch

#### 4.2 Configure Provider Settings

**Client ID and Secret:**
```
Client ID: [paste-your-client-id]
Client Secret: [paste-your-client-secret]
```

**Additional Settings:**
```
Redirect URL: https://[project-ref].supabase.co/auth/v1/callback
Skip nonce check: false (recommended)
```

**Scopes (Advanced):**
```
Default: email profile
Custom: email profile openid
```

4. **Click** "Save"

#### 4.3 Verify Configuration

1. **Check** the provider status shows "Enabled"
2. **Note** the callback URL for reference
3. **Test** configuration (see Testing section below)

---

## GitHub OAuth Setup

### Overview

GitHub OAuth integration allows users to sign in using their GitHub accounts. This is particularly useful for developer-focused applications and provides access to user profile information and public repositories.

### Step 1: GitHub OAuth Application Setup

#### 1.1 Access Developer Settings

1. **Navigate** to [GitHub](https://github.com) and sign in
2. **Click** your profile picture in the top-right corner
3. **Select** "Settings" from the dropdown
4. **Scroll** down and click "Developer settings" in the left sidebar
5. **Click** "OAuth Apps" in the left sidebar

#### 1.2 Create New OAuth App

1. **Click** "New OAuth App" button
2. **Fill** in the application details:

**Application Information:**
```
Application name: TripSage
Homepage URL: https://your-domain.com
Application description: AI-powered travel planning platform
```

**Authorization callback URL:**
```
https://[project-ref].supabase.co/auth/v1/callback
```

**For development, you may also need:**
```
http://localhost:3000/auth/callback
```

3. **Click** "Register application"

#### 1.3 Configure Application Settings

**Optional Settings:**
```
✅ Enable Device Flow: false (not needed for web apps)
✅ Request user authorization (OAuth): true
✅ Expire user authorization tokens: false (optional)
```

**Upload Application Logo:**
1. **Click** "Upload new logo"
2. **Upload** TripSage logo (minimum 200x200px)
3. **Adjust** logo positioning if needed

### Step 2: Client Credentials Management

#### 2.1 Generate Client Secret

1. **Locate** "Client secrets" section
2. **Click** "Generate a new client secret"
3. **Copy** the generated secret immediately (it won't be shown again)

**Save the following credentials:**
```
Client ID: [alphanumeric-string]
Client Secret: [secret-string]
```

⚠️ **Security Note**: Store these credentials securely and never commit them to version control.

#### 2.2 Configure Webhook (Optional)

For advanced integrations:
1. **Click** "Add webhook"
2. **Set** Payload URL: `https://your-domain.com/api/webhooks/github`
3. **Select** Content type: `application/json`
4. **Choose** events: User, Repository (as needed)

### Step 3: Supabase GitHub Provider Configuration

#### 3.1 Enable GitHub Provider

1. **Open** Supabase Dashboard
2. **Navigate** to your TripSage project
3. **Go** to **Authentication** → **Providers**
4. **Locate** "GitHub" provider
5. **Toggle** the enable switch

#### 3.2 Configure Provider Settings

**Basic Configuration:**
```
Client ID: [paste-github-client-id]
Client Secret: [paste-github-client-secret]
```

**Advanced Settings:**
```
Redirect URL: https://[project-ref].supabase.co/auth/v1/callback
```

**Scopes Configuration:**
```
Default: user:email
Recommended: user:email read:user
```

**Additional Scopes (Optional):**
```
user:email        (Required - email access)
read:user         (Recommended - profile info)
public_repo       (Optional - public repository access)
```

4. **Click** "Save"

#### 3.3 Verify Configuration

1. **Confirm** provider status shows "Enabled"
2. **Check** callback URL matches GitHub app settings
3. **Test** authentication flow (see Testing section)

---

## Configuration Management

### Environment Variables

#### Development Environment (`.env.local`)

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OAuth Development Settings (Optional - managed in Supabase)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Development URLs
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Production Environment

```bash
# Supabase Production Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-production-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-production-service-role-key

# Production URLs
NEXT_PUBLIC_APP_URL=https://your-domain.com
NEXT_PUBLIC_API_URL=https://api.your-domain.com

# Security Settings
NODE_ENV=production
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=https://your-domain.com
```

#### Environment Variable Security

**Development:**
- Use `.env.local` (automatically ignored by Git)
- Never commit OAuth secrets to version control
- Use different secrets for development and production

**Production:**
- Use secure environment variable management (Vercel, AWS Secrets Manager, etc.)
- Enable secret rotation policies
- Monitor secret access logs

### Frontend Configuration

#### OAuth Integration Code

The OAuth functionality is already implemented in TripSage. Here's how it works:

**Login Component (`src/components/auth/login-form.tsx`):**
```typescript
import { useAuth } from '@/contexts/auth-context';

export function LoginForm() {
  const { signInWithOAuth, isLoading, error } = useAuth();

  const handleOAuthSignIn = async (provider: 'google' | 'github') => {
    try {
      await signInWithOAuth(provider);
    } catch (error) {
      console.error(`${provider} sign-in failed:`, error);
    }
  };

  return (
    <div className="oauth-buttons">
      <Button 
        onClick={() => handleOAuthSignIn('google')}
        disabled={isLoading}
        variant="outline"
        className="w-full"
      >
        <GoogleIcon className="mr-2 h-4 w-4" />
        Continue with Google
      </Button>
      
      <Button 
        onClick={() => handleOAuthSignIn('github')}
        disabled={isLoading}
        variant="outline"
        className="w-full"
      >
        <GitHubIcon className="mr-2 h-4 w-4" />
        Continue with GitHub
      </Button>
    </div>
  );
}
```

#### OAuth Flow Implementation

**Auth Context (`src/contexts/auth-context.tsx`):**
```typescript
const signInWithOAuth = async (provider: 'google' | 'github') => {
  try {
    setAuthState({ isLoading: true, error: null });

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    });

    if (error) {
      setAuthState({ error: error.message, isLoading: false });
      return;
    }

    // Redirect happens automatically
  } catch (error) {
    setAuthState({
      error: error instanceof Error ? error.message : `Failed to sign in with ${provider}`,
      isLoading: false,
    });
  }
};
```

#### OAuth Callback Handler

**Callback Page (`src/app/auth/callback/page.tsx`):**
```typescript
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSupabase } from '@/lib/supabase/client';

export default function AuthCallback() {
  const router = useRouter();
  const supabase = useSupabase();

  useEffect(() => {
    const handleAuthCallback = async () => {
      const { data, error } = await supabase.auth.getSession();
      
      if (error) {
        console.error('Auth callback error:', error);
        router.push('/login?error=oauth_callback_failed');
        return;
      }

      if (data?.session) {
        router.push('/dashboard');
      } else {
        router.push('/login');
      }
    };

    handleAuthCallback();
  }, [router, supabase.auth]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
        <p className="mt-2 text-sm text-gray-600">Completing sign-in...</p>
      </div>
    </div>
  );
}
```

---

## Security Best Practices

### OAuth Security Guidelines

#### 1. Secure Credential Management

**Do:**
- ✅ Store credentials in secure environment variables
- ✅ Use different secrets for development and production
- ✅ Implement secret rotation policies
- ✅ Monitor secret access and usage

**Don't:**
- ❌ Commit OAuth secrets to version control
- ❌ Share secrets in plain text communications
- ❌ Use the same secrets across environments
- ❌ Store secrets in client-side code

#### 2. Redirect URI Security

**Best Practices:**
```
✅ Use HTTPS in production
✅ Whitelist specific domains only
✅ Avoid wildcard patterns
✅ Validate redirect URIs server-side
```

**Secure Redirect URI Examples:**
```
Production:
https://your-domain.com/auth/callback
https://api.your-domain.com/auth/callback

Development:
http://localhost:3000/auth/callback
http://127.0.0.1:3000/auth/callback
```

#### 3. OAuth Scope Management

**Principle of Least Privilege:**
```
Google Scopes:
- email (required)
- profile (recommended)
- openid (required for OIDC)

GitHub Scopes:
- user:email (required)
- read:user (recommended)
```

**Avoid Over-Privileged Scopes:**
```
❌ Avoid: repo, admin:*, delete:*
✅ Use: read:user, user:email
```

#### 4. Session Security

**Configuration in Supabase:**
```
JWT Expiry: 3600 seconds (1 hour)
Refresh Token Rotation: Enabled
Auto Refresh Token: Enabled
JWT Secret: Secure random string
```

**Client-Side Security:**
```typescript
// Implement automatic token refresh
useEffect(() => {
  const { data: { subscription } } = supabase.auth.onAuthStateChange(
    (event, session) => {
      if (event === 'TOKEN_REFRESHED') {
        console.log('Token refreshed successfully');
      }
    }
  );
  
  return () => subscription.unsubscribe();
}, []);
```

### Security Monitoring

#### 1. Audit Logging

**Enable in Supabase:**
- Authentication events logging
- Failed login attempt monitoring
- Unusual access pattern detection

**Custom Logging:**
```typescript
const logAuthEvent = async (event: string, provider: string, userId?: string) => {
  await supabase.from('auth_logs').insert({
    event_type: event,
    provider: provider,
    user_id: userId,
    timestamp: new Date().toISOString(),
    ip_address: req.ip,
    user_agent: req.headers['user-agent']
  });
};
```

#### 2. Rate Limiting

**Implement OAuth rate limiting:**
```typescript
// In your API middleware
const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 OAuth attempts per window
  message: 'Too many OAuth attempts, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
});
```

---

## Testing and Validation

### Development Testing

#### 1. Local Testing Setup

**Prerequisites:**
```bash
# Start development server
cd frontend && pnpm dev

# Verify environment variables
echo $NEXT_PUBLIC_SUPABASE_URL
echo $NEXT_PUBLIC_SUPABASE_ANON_KEY
```

**Test Checklist:**
```
✅ Google OAuth flow works locally
✅ GitHub OAuth flow works locally
✅ User profile data is correctly retrieved
✅ Session persistence works across page refreshes
✅ Logout functionality works properly
```

#### 2. OAuth Flow Testing

**Google OAuth Test:**
1. Navigate to `http://localhost:3000/login`
2. Click "Continue with Google"
3. Complete Google authorization
4. Verify redirect to dashboard
5. Check user profile data in Supabase

**GitHub OAuth Test:**
1. Navigate to `http://localhost:3000/login`
2. Click "Continue with GitHub"
3. Complete GitHub authorization
4. Verify redirect to dashboard
5. Check user profile data in Supabase

#### 3. Automated Testing

**OAuth Integration Tests:**
```typescript
// tests/auth/oauth.test.ts
import { test, expect } from '@playwright/test';

test.describe('OAuth Authentication', () => {
  test('Google OAuth flow completes successfully', async ({ page }) => {
    await page.goto('/login');
    
    // Mock OAuth provider response
    await page.route('**/auth/v1/authorize**', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ access_token: 'mock-token' })
      });
    });
    
    await page.click('[data-testid="google-oauth-button"]');
    await expect(page).toHaveURL('/dashboard');
  });
  
  test('handles OAuth errors gracefully', async ({ page }) => {
    await page.goto('/login');
    
    // Mock OAuth error
    await page.route('**/auth/v1/authorize**', (route) => {
      route.fulfill({
        status: 400,
        body: JSON.stringify({ error: 'invalid_request' })
      });
    });
    
    await page.click('[data-testid="google-oauth-button"]');
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  });
});
```

### Production Testing

#### 1. Pre-Production Checklist

**OAuth Provider Configuration:**
```
✅ Production redirect URIs configured
✅ OAuth consent screen approved (Google)
✅ Application verified (GitHub)
✅ HTTPS enabled on all domains
✅ SSL certificates valid
```

**Supabase Configuration:**
```
✅ Production OAuth credentials configured
✅ Rate limiting enabled
✅ Email verification enabled
✅ Security policies configured
```

#### 2. Production Deployment Testing

**Test Scenarios:**
1. **New User Registration:**
   - OAuth sign-up creates user account
   - User profile data correctly stored
   - Welcome email sent (if configured)

2. **Existing User Sign-In:**
   - OAuth sign-in works for existing users
   - Profile data updated if changed
   - Session restored properly

3. **Error Scenarios:**
   - OAuth cancellation handled gracefully
   - Provider errors displayed appropriately
   - Network errors don't break flow

#### 3. Monitoring and Alerts

**Set up monitoring for:**
```
✅ OAuth success/failure rates
✅ Provider response times
✅ Authentication errors
✅ Session duration metrics
✅ User profile update failures
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Google OAuth Issues

**Issue: "Error 400: invalid_request"**
```
Causes:
- Incorrect redirect URI configuration
- Missing required OAuth scopes
- Invalid client ID format

Solutions:
1. Verify redirect URI matches exactly in Google Console
2. Check client ID format (.apps.googleusercontent.com)
3. Ensure OAuth consent screen is published
```

**Issue: "Access blocked: This app's request is invalid"**
```
Causes:
- OAuth consent screen not configured
- App not verified for production use
- Restricted domain policy in Google Workspace

Solutions:
1. Complete OAuth consent screen setup
2. Submit app for verification if needed
3. Add domain to authorized list in Google Workspace
```

**Issue: "Error 403: access_denied"**
```
Causes:
- User denied OAuth permission
- App not approved for requested scopes
- Domain restrictions in place

Solutions:
1. Review requested OAuth scopes
2. Ensure minimal necessary permissions
3. Check domain authorization settings
```

#### 2. GitHub OAuth Issues

**Issue: "The redirect_uri MUST match the registered callback URL"**
```
Causes:
- Redirect URI mismatch between GitHub app and Supabase
- HTTP vs HTTPS protocol mismatch
- Missing or incorrect port numbers

Solutions:
1. Verify exact URI match in GitHub app settings
2. Ensure protocol consistency (HTTPS in production)
3. Update GitHub app callback URL if needed
```

**Issue: "Bad verification code"**
```
Causes:
- Expired authorization code
- Code reuse attempt
- Network connectivity issues

Solutions:
1. Retry OAuth flow with fresh authorization
2. Check network connectivity
3. Verify GitHub app credentials in Supabase
```

#### 3. Supabase Integration Issues

**Issue: "OAuth provider not configured"**
```
Causes:
- Provider not enabled in Supabase dashboard
- Incorrect client credentials
- Missing environment variables

Solutions:
1. Enable provider in Authentication → Providers
2. Verify client ID and secret configuration
3. Check environment variable setup
```

**Issue: "Invalid JWT token"**
```
Causes:
- Expired or malformed JWT
- JWT secret mismatch
- Clock skew between servers

Solutions:
1. Refresh authentication token
2. Verify JWT secret configuration
3. Check server time synchronization
```

### Debugging Tools and Techniques

#### 1. Browser Developer Tools

**Network Tab Analysis:**
```
1. Open Developer Tools → Network tab
2. Filter by "Auth" or "XHR"
3. Look for OAuth redirect requests
4. Check response status codes and headers
5. Examine callback URL parameters
```

**Console Debugging:**
```typescript
// Add debug logging to auth context
const signInWithOAuth = async (provider: 'google' | 'github') => {
  console.log(`Starting OAuth flow for ${provider}`);
  
  try {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    
    console.log('OAuth response:', { data, error });
    
    if (error) {
      console.error('OAuth error:', error);
    }
  } catch (error) {
    console.error('OAuth exception:', error);
  }
};
```

#### 2. Supabase Debugging

**Auth Logs Analysis:**
1. Go to Supabase Dashboard → Authentication → Users
2. Check recent authentication events
3. Look for error messages and failure patterns
4. Review user metadata and provider information

**SQL Query Debugging:**
```sql
-- Check user authentication events
SELECT 
  email,
  provider,
  created_at,
  last_sign_in_at,
  raw_user_meta_data
FROM auth.users 
WHERE provider IN ('google', 'github')
ORDER BY created_at DESC 
LIMIT 10;

-- Check authentication audit logs
SELECT 
  event_type,
  error_message,
  ip_address,
  created_at
FROM auth.audit_log_entries 
WHERE event_type LIKE '%oauth%'
ORDER BY created_at DESC 
LIMIT 20;
```

#### 3. Provider-Specific Debugging

**Google OAuth Debugging:**
```
1. Check Google Cloud Console → APIs & Services → Credentials
2. Review OAuth 2.0 client IDs usage statistics
3. Check OAuth consent screen status
4. Verify API quotas and limits
```

**GitHub OAuth Debugging:**
```
1. Check GitHub Developer Settings → OAuth Apps
2. Review application usage statistics
3. Check webhook delivery logs (if configured)
4. Verify OAuth app permissions and scopes
```

### Support and Resources

#### 1. Documentation Links

**Official Documentation:**
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)

**Community Resources:**
- [Supabase Community Discord](https://discord.supabase.com/)
- [Stack Overflow - Supabase Auth](https://stackoverflow.com/questions/tagged/supabase+authentication)
- [GitHub Issues - Supabase](https://github.com/supabase/supabase/issues)

#### 2. Getting Help

**Before Reaching Out:**
1. Check this troubleshooting guide
2. Review Supabase dashboard logs
3. Test with provider's OAuth playground tools
4. Search community forums for similar issues

**When Contacting Support:**
Include the following information:
- OAuth provider (Google/GitHub)
- Error messages (exact text)
- Browser and version
- Steps to reproduce
- Supabase project reference ID
- Screenshots of error screens

---

## Advanced Configuration

### Custom OAuth Flows

#### 1. Custom Callback Handling

For advanced use cases, you can implement custom OAuth callback logic:

```typescript
// pages/api/auth/callback.ts
import { createServerSupabaseClient } from '@supabase/auth-helpers-nextjs';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const supabase = createServerSupabaseClient({ req, res });
  
  const { code, state } = req.query;
  
  if (code) {
    const { data, error } = await supabase.auth.exchangeCodeForSession(String(code));
    
    if (error) {
      return res.redirect('/login?error=oauth_callback_failed');
    }
    
    // Custom logic after successful OAuth
    const { user } = data;
    
    // Update user profile, create welcome data, etc.
    await updateUserProfile(user);
    
    return res.redirect('/dashboard');
  }
  
  return res.redirect('/login');
}
```

#### 2. Multi-Tenant OAuth Configuration

For applications serving multiple organizations:

```typescript
// Tenant-specific OAuth configuration
const getOAuthConfig = (tenantId: string) => {
  return {
    google: {
      clientId: process.env[`GOOGLE_CLIENT_ID_${tenantId.toUpperCase()}`],
      clientSecret: process.env[`GOOGLE_CLIENT_SECRET_${tenantId.toUpperCase()}`],
    },
    github: {
      clientId: process.env[`GITHUB_CLIENT_ID_${tenantId.toUpperCase()}`],
      clientSecret: process.env[`GITHUB_CLIENT_SECRET_${tenantId.toUpperCase()}`],
    }
  };
};
```

#### 3. OAuth with Custom Claims

Add custom claims to OAuth tokens:

```typescript
// Supabase Edge Function for custom claims
export default async function handler(req: Request) {
  const { user, provider } = await req.json();
  
  // Add custom claims based on provider
  const customClaims = {
    role: 'user',
    provider: provider,
    plan: 'free',
    features: ['trip_planning', 'basic_search']
  };
  
  // Update user metadata
  const { error } = await supabase.auth.admin.updateUserById(
    user.id,
    { 
      user_metadata: { 
        ...user.user_metadata, 
        ...customClaims 
      } 
    }
  );
  
  return new Response(JSON.stringify({ success: !error }));
}
```

### Performance Optimization

#### 1. OAuth Response Caching

Implement caching for OAuth provider responses:

```typescript
const oauthCache = new Map();

const getCachedUserInfo = async (provider: string, accessToken: string) => {
  const cacheKey = `${provider}:${accessToken}`;
  
  if (oauthCache.has(cacheKey)) {
    return oauthCache.get(cacheKey);
  }
  
  const userInfo = await fetchUserInfo(provider, accessToken);
  
  // Cache for 5 minutes
  oauthCache.set(cacheKey, userInfo);
  setTimeout(() => oauthCache.delete(cacheKey), 5 * 60 * 1000);
  
  return userInfo;
};
```

#### 2. Parallel OAuth Provider Setup

Load multiple OAuth providers in parallel:

```typescript
const initializeOAuthProviders = async () => {
  const providers = ['google', 'github'];
  
  const providerConfigs = await Promise.all(
    providers.map(async (provider) => {
      const config = await loadProviderConfig(provider);
      return { provider, config };
    })
  );
  
  return providerConfigs.reduce((acc, { provider, config }) => {
    acc[provider] = config;
    return acc;
  }, {});
};
```

---

## Summary

This comprehensive OAuth setup guide provides everything needed to implement secure Google and GitHub authentication in TripSage:

### Key Achievements
- ✅ **Detailed Provider Setup**: Step-by-step Google and GitHub OAuth configuration
- ✅ **Security Best Practices**: Comprehensive security guidelines and monitoring
- ✅ **Testing Framework**: Development and production testing procedures
- ✅ **Troubleshooting Guide**: Common issues and debugging techniques
- ✅ **Advanced Features**: Custom flows and performance optimizations

### Next Steps
1. **Complete Provider Setup**: Follow the step-by-step instructions for both Google and GitHub
2. **Implement Security Measures**: Apply all recommended security practices
3. **Test Thoroughly**: Use the provided testing framework
4. **Monitor and Maintain**: Set up monitoring and regular security reviews

### Quick Reference
- **Google Console**: [console.cloud.google.com](https://console.cloud.google.com/)
- **GitHub Settings**: [github.com/settings/developers](https://github.com/settings/developers)
- **Supabase Dashboard**: Your project's authentication settings
- **Documentation**: Refer to the troubleshooting section for common issues

---

*Last updated: 2025-11-06*  
*OAuth Setup Guide: Complete*  
*Covers: Google OAuth 2.0, GitHub OAuth, Security, Testing, Troubleshooting*