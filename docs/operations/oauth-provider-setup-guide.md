# Authentication Guide

TripSage uses Supabase for authentication with OAuth support for Google and GitHub.

## Prerequisites

- Supabase project with authentication enabled
- Admin access to Supabase dashboard
- HTTPS domain for production deployment

## OAuth Setup

TripSage supports OAuth authentication through Supabase for Google and GitHub providers.

### Provider Configuration

1. **Access Supabase Dashboard**
   - Navigate to your project
   - Go to Authentication → Providers

2. **Enable OAuth Providers**
   - Toggle Google provider to enable
   - Toggle GitHub provider to enable

3. **Configure Provider Settings**
   - Add client credentials from provider consoles
   - Set redirect URL to: `https://[project-ref].supabase.co/auth/v1/callback`
   - Configure required scopes (email, profile)

### Provider-Specific Setup

**Google OAuth:**

- Create project in Google Cloud Console
- Enable Google+ API or People API
- Create OAuth 2.0 credentials
- Configure authorized redirect URIs

**GitHub OAuth:**

- Create OAuth App in GitHub Developer Settings
- Set Authorization callback URL
- Generate client secret

## Environment Configuration

### Required Variables

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Production URLs
NEXT_PUBLIC_APP_URL=https://your-domain.com
NEXTAUTH_URL=https://your-domain.com
```

### Development Setup

```bash
# Development URLs
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXTAUTH_URL=http://localhost:3000
```

## Testing

### Development Testing

1. **Start development server**

   ```bash
   cd frontend && pnpm dev
   ```

2. **Test OAuth flows**
   - Navigate to `/login`
   - Click Google/GitHub OAuth buttons
   - Complete provider authorization
   - Verify redirect to dashboard

3. **Check Supabase dashboard**
   - View user records in Authentication → Users
   - Verify provider metadata

### Production Testing

- Verify HTTPS redirect URIs are configured
- Test OAuth flows in production environment
- Check Supabase authentication logs

## Troubleshooting

### Common Issues

**OAuth provider not configured:**

- Enable provider in Supabase Authentication → Providers
- Verify client credentials are correct

**Invalid redirect URI:**

- Ensure redirect URI matches: `https://[project-ref].supabase.co/auth/v1/callback`
- Use HTTPS in production

**Authentication errors:**

- Check Supabase dashboard for error logs
- Verify environment variables are set correctly
- Test provider credentials in their respective consoles

### Debugging

- Check browser network tab for OAuth requests
- Review Supabase Authentication → Logs
- Verify provider app settings match Supabase configuration

## Resources

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Google OAuth Setup](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Setup](https://docs.github.com/en/developers/apps/building-oauth-apps)
