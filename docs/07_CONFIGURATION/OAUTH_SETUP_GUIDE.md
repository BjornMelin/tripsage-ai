# OAuth Provider Setup Guide

This guide walks you through setting up OAuth providers for TripSage authentication.

## Prerequisites

- Supabase project with authentication enabled
- OAuth provider accounts (Google, GitHub, etc.)
- Admin access to your Supabase dashboard

## Supported Providers

- ✅ Google OAuth 2.0
- ✅ GitHub OAuth
- 🔄 Facebook (configurable)
- 🔄 Microsoft (configurable)
- 🔄 Apple Sign-In (configurable)

## Google OAuth Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API

### 2. Configure OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen**
2. Choose **External** user type
3. Fill in required information:
   - App name: "TripSage"
   - User support email: your email
   - Developer contact information: your email

### 3. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Choose **Web application**
4. Add authorized redirect URIs:
   ```
   https://your-project-ref.supabase.co/auth/v1/callback
   http://localhost:3000/auth/callback (for development)
   ```
5. Save your **Client ID** and **Client Secret**

### 4. Configure in Supabase

1. Go to your Supabase dashboard
2. Navigate to **Authentication** → **Providers**
3. Enable **Google** provider
4. Enter your **Client ID** and **Client Secret**
5. Save the configuration

## GitHub OAuth Setup

### 1. Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in the application details:
   - Application name: "TripSage"
   - Homepage URL: `https://your-domain.com`
   - Authorization callback URL: `https://your-project-ref.supabase.co/auth/v1/callback`

### 2. Configure in Supabase

1. Go to your Supabase dashboard
2. Navigate to **Authentication** → **Providers**
3. Enable **GitHub** provider
4. Enter your **Client ID** and **Client Secret**
5. Save the configuration

## Environment Variables

Add these to your `.env.local` file:

```bash
# OAuth Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# OAuth Provider Settings (optional - managed in Supabase)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

## Frontend Configuration

The OAuth buttons are already implemented in the login form. No additional frontend configuration is needed.

### How OAuth Works in TripSage

1. User clicks OAuth provider button
2. Redirected to provider's authorization page
3. User grants permission
4. Provider redirects back to `/auth/callback`
5. Supabase exchanges code for tokens
6. User is redirected to dashboard

## Testing OAuth Integration

### Development Testing

1. Start your development server:
   ```bash
   cd frontend && pnpm dev
   ```

2. Navigate to `/login`
3. Click on Google or GitHub button
4. Complete the OAuth flow
5. Verify redirection to dashboard

### Production Testing

1. Deploy your application
2. Update OAuth redirect URIs to use production URLs
3. Test the complete flow

## Troubleshooting

### Common Issues

**"Invalid redirect URI"**
- Ensure redirect URIs match exactly in OAuth provider settings
- Check for trailing slashes or protocol mismatches

**"OAuth provider not configured"**
- Verify provider is enabled in Supabase
- Check Client ID and Secret are correct

**"Access denied"**
- Check OAuth consent screen configuration
- Ensure user email is authorized (for restricted apps)

### Debug Mode

Enable debug mode in development:

```typescript
// In your auth context
const { error } = await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: {
    redirectTo: `${window.location.origin}/auth/callback`,
    queryParams: {
      access_type: 'offline',
      prompt: 'consent',
    },
  },
});
```

## Security Best Practices

1. **Use HTTPS in production**
2. **Restrict redirect URIs** to known domains
3. **Enable email verification** in Supabase
4. **Monitor OAuth usage** in provider dashboards
5. **Rotate secrets regularly**

## Next Steps

After setting up OAuth:

1. Test the authentication flow
2. Configure user profile mapping
3. Set up user roles and permissions
4. Implement logout handling
5. Add security monitoring

## Support

For issues with OAuth setup:

1. Check Supabase logs in the dashboard
2. Review browser console for errors
3. Verify provider configuration
4. Contact support if needed