# JWT Security Configuration Guide

## Overview

TripSage uses JWT (JSON Web Tokens) for authentication across the platform. This document outlines the security requirements and best practices for JWT configuration.

## JWT Secret Requirements

### Production Requirements

**⚠️ CRITICAL SECURITY REQUIREMENT**: The `JWT_SECRET` environment variable MUST be set in production environments.

- **Length**: Minimum 32 bytes (256 bits) of entropy
- **Format**: Base64-encoded random string
- **Uniqueness**: Different secret for each environment (staging, production)
- **Storage**: Use secure secret management (AWS Secrets Manager, HashiCorp Vault, etc.)

### Generating a Secure JWT Secret

#### Option 1: Using OpenSSL (Recommended)
```bash
openssl rand -base64 32
```

#### Option 2: Using Node.js
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

#### Option 3: Using npm script (Frontend)
```bash
cd frontend
npm run generate:jwt-secret
```

## Environment Configuration

### Frontend (.env.local)
```bash
# REQUIRED: JWT Secret for authentication
JWT_SECRET=your_generated_secret_here
```

### Backend (.env)
```bash
# Security settings
JWT_SECRET=your_generated_secret_here  # Must match frontend secret
```

## Security Implementation

### Middleware Protection

The frontend middleware (`src/middleware.ts`) implements strict JWT validation:

```typescript
const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET ?? (() => {
    if (process.env.NODE_ENV === "development") {
      // Development fallback with warning
      console.warn("⚠️  JWT_SECRET not set...");
      return "dev-only-secret-" + Math.random().toString(36);
    }
    // Production requirement - throws error
    throw new Error("SECURITY ERROR: JWT_SECRET required");
  })()
);
```

### Server Actions Protection

Server-side authentication (`src/lib/auth/server-actions.ts`) uses the same validation pattern.

## Security Best Practices

### 1. Secret Rotation
- Rotate JWT secrets every 90 days
- Implement graceful rotation with overlap period
- Maintain previous secret for token validation during rotation

### 2. Token Configuration
- **Expiration**: 7 days for regular tokens
- **Refresh**: Automatic refresh when <24 hours remaining
- **Algorithm**: HS256 (HMAC with SHA-256)

### 3. Cookie Security
```typescript
const COOKIE_OPTIONS = {
  httpOnly: true,              // Prevent XSS attacks
  secure: true,                // HTTPS only in production
  sameSite: "strict",          // CSRF protection
  maxAge: 60 * 60 * 24 * 7,   // 7 days
  path: "/",
};
```

### 4. Production Checklist

- [ ] Generate unique JWT_SECRET for production
- [ ] Store secret in secure secret management system
- [ ] Enable HTTPS for secure cookie transmission
- [ ] Configure proper CORS settings
- [ ] Implement rate limiting on authentication endpoints
- [ ] Enable audit logging for authentication events
- [ ] Set up monitoring for failed authentication attempts

## Common Issues

### Issue: "JWT_SECRET environment variable is required in production"
**Solution**: Set the JWT_SECRET environment variable before starting the application.

### Issue: "Invalid token" errors after deployment
**Solution**: Ensure the same JWT_SECRET is used across all services (frontend and backend).

### Issue: Authentication works locally but not in production
**Solution**: Check that cookies are configured for HTTPS and the correct domain.

## Security Incident Response

If a JWT secret is compromised:

1. **Immediate Actions**:
   - Generate new JWT secret
   - Deploy with new secret immediately
   - Force logout all users (invalidate existing tokens)

2. **Follow-up Actions**:
   - Audit logs for suspicious activity
   - Notify affected users if necessary
   - Review and improve secret management practices

## References

- [JWT Best Practices (RFC 8725)](https://tools.ietf.org/html/rfc8725)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [Next.js Security Headers](https://nextjs.org/docs/app/building-your-application/configuring/security)