# 🔒 TripSage Authentication API

> **Complete Authentication Reference**  
> JWT tokens, API keys, OAuth flows, and security best practices for TripSage API

## 📋 Table of Contents

- [Authentication Overview](#authentication-overview)
- [JWT Authentication](#jwt-authentication)
- [API Key Authentication (BYOK)](#api-key-authentication)
- [OAuth 2.0 Integration](#oauth-20-integration)
- [Permission Scopes](#permission-scopes)
- [Security Best Practices](#security-best-practices)
- [Rate Limiting](#rate-limiting)
- [Troubleshooting](#troubleshooting)

---

## Authentication Overview

TripSage supports multiple authentication methods for different use cases:

| Method | Use Case | Security Level | Expiration |
|--------|----------|----------------|------------|
| **JWT Tokens** | User-facing applications | High | 1 hour (access), 30 days (refresh) |
| **API Keys** | Server-to-server integration | High | Configurable (up to 1 year) |
| **OAuth 2.0** | Third-party integrations | High | Based on provider |

### Base URLs

- **Production**: `https://api.tripsage.ai`
- **Development**: `http://localhost:8001`

---

## JWT Authentication

### User Registration

Create a new user account.

```http
POST /api/auth/register
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "secure_password123",
  "name": "John Doe",
  "preferences": {
    "currency": "USD",
    "language": "en",
    "timezone": "America/New_York"
  }
}
```

**Response (201 Created):**

```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "name": "John Doe",
    "email_verified": false,
    "created_at": "2025-01-15T10:30:00Z"
  },
  "message": "Registration successful. Please verify your email."
}
```

### User Login

Authenticate and receive JWT tokens.

```http
POST /api/auth/login
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "secure_password123"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "name": "John Doe",
    "email_verified": true,
    "preferences": {
      "currency": "USD",
      "language": "en",
      "timezone": "America/New_York"
    }
  }
}
```

### Token Refresh

Refresh an expired access token using a refresh token.

```http
POST /api/auth/refresh
Content-Type: application/json
```

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using JWT Tokens

Include the access token in the Authorization header:

```http
GET /api/trips
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Logout

Invalidate tokens and end session.

```http
POST /api/auth/logout
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**

```json
{
  "message": "Successfully logged out"
}
```

---

## API Key Authentication

### BYOK (Bring Your Own Key) Support

TripSage supports storing and managing your third-party API keys securely. You can add API keys for services like Duffel (flights), Google Maps, and weather services to enhance your travel planning experience.

### Manage Your API Keys

#### List Your API Keys

Get all API keys you've stored in TripSage.

```http
GET /api/keys
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**

```json
{
  "api_keys": [
    {
      "id": "key_123abc",
      "name": "My Duffel API Key",
      "service": "duffel",
      "description": "For flight search integration",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z",
      "expires_at": "2026-01-15T10:30:00Z",
      "is_valid": true,
      "last_used": "2025-06-17T12:00:00Z"
    }
  ],
  "count": 1
}
```

#### Add a New API Key

Store a new third-party API key securely.

```http
POST /api/keys
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "My Duffel API Key",
  "service": "duffel",
  "key": "duffel_test_your_actual_api_key_here",
  "description": "For flight search and booking",
  "expires_at": "2026-01-15T10:30:00Z"
}
```

**Response (201 Created):**

```json
{
  "id": "key_123abc",
  "name": "My Duffel API Key",
  "service": "duffel",
  "description": "For flight search and booking",
  "created_at": "2025-06-17T10:30:00Z",
  "updated_at": "2025-06-17T10:30:00Z",
  "expires_at": "2026-01-15T10:30:00Z",
  "is_valid": true,
  "last_used": null
}
```

**Supported Services:**

| Service | Description | Key Format |
|---------|-------------|------------|
| `duffel` | Flight search and booking | `duffel_test_*` or `duffel_live_*` |
| `google_maps` | Maps and location services | Google Cloud API key |
| `openweather` | Weather information | OpenWeatherMap API key |

#### Validate an API Key

Test if your API key is working with the external service.

```http
POST /api/keys/validate
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "key": "duffel_test_your_actual_api_key_here",
  "service": "duffel"
}
```

**Response (200 OK):**

```json
{
  "is_valid": true,
  "service": "duffel",
  "message": "Valid Duffel API key"
}
```

**Response (400 Bad Request) - Invalid Key:**

```json
{
  "is_valid": false,
  "service": "duffel",
  "message": "Invalid or expired Duffel API key"
}
```

#### Update/Rotate an API Key

Replace an existing API key with a new one.

```http
POST /api/keys/{key_id}/rotate
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "new_key": "duffel_live_your_new_api_key_here"
}
```

**Response (200 OK):**

```json
{
  "id": "key_123abc",
  "name": "My Duffel API Key",
  "service": "duffel",
  "description": "For flight search and booking",
  "created_at": "2025-06-17T10:30:00Z",
  "updated_at": "2025-06-17T15:45:00Z",
  "expires_at": "2026-01-15T10:30:00Z",
  "is_valid": true,
  "last_used": null
}
```

#### Remove an API Key

Delete a stored API key.

```http
DELETE /api/keys/{key_id}
Authorization: Bearer {jwt_token}
```

**Response (204 No Content)**

### Security & Best Practices

#### Secure Storage

- **Envelope Encryption**: Your API keys are encrypted using industry-standard envelope encryption
- **Key Hashing**: Deduplication without storing plaintext keys
- **Audit Logging**: All key operations are logged for security monitoring

#### API Key Management Tips

1. **Use Descriptive Names**: Help identify keys later
   ```json
   {
     "name": "Production Duffel Key - Main Account",
     "description": "Primary flight search for production environment"
   }
   ```

2. **Set Expiration Dates**: Regularly rotate your keys
   ```json
   {
     "expires_at": "2026-01-15T10:30:00Z"
   }
   ```

3. **Monitor Usage**: Check the `last_used` field to identify unused keys

4. **Validate Before Storing**: Always validate keys before adding them
   ```bash
   # Test your key first
   curl -X POST https://api.tripsage.ai/api/keys/validate \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"key": "your_api_key", "service": "duffel"}'
   ```

#### Getting API Keys from Providers

**Duffel (Flights)**
1. Sign up at [duffel.com](https://duffel.com)
2. Navigate to API Settings
3. Generate a new API key
4. Use the test key format: `duffel_test_*`

**Google Maps**
1. Visit [Google Cloud Console](https://console.cloud.google.com)
2. Enable Maps JavaScript API
3. Create credentials → API Key
4. Restrict to your domains for security

**OpenWeatherMap**
1. Register at [openweathermap.org](https://openweathermap.org/api)
2. Get your free API key
3. Note: Free tier has rate limits

### Example Integration

#### Using Your Stored API Keys

Once you've stored your API keys, TripSage will automatically use them for enhanced features:

```javascript
// Your frontend code remains the same
const flights = await fetch('/api/flights/search', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    origin: 'JFK',
    destination: 'LAX',
    departure_date: '2025-07-01'
  })
});

// TripSage automatically uses your stored Duffel API key
// No need to include it in the request
```


---

## OAuth 2.0 Integration

### Supported Providers

| Provider | Scope | Redirect URI |
|----------|-------|--------------|
| Google | `openid email profile` | `/api/auth/oauth/google/callback` |
| GitHub | `user:email` | `/api/auth/oauth/github/callback` |
| Microsoft | `openid email profile` | `/api/auth/oauth/microsoft/callback` |

### OAuth Flow

#### 1. Initiate OAuth Flow

```http
GET /api/auth/oauth/{provider}/authorize?redirect_uri={your_redirect_uri}
```

**Parameters:**

- `provider`: `google`, `github`, or `microsoft`
- `redirect_uri`: Your application's callback URL

**Response:** Redirects to provider's authorization page

#### 2. Handle Callback

After user authorization, the provider redirects to:

```text
{your_redirect_uri}?code={authorization_code}&state={state}
```

#### 3. Exchange Code for Tokens

```http
POST /api/auth/oauth/{provider}/callback
Content-Type: application/json
```

**Request Body:**

```json
{
  "code": "authorization_code_from_provider",
  "redirect_uri": "https://yourapp.com/auth/callback"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "name": "John Doe",
    "provider": "google",
    "provider_id": "google_user_id"
  }
}
```

---

## Permission Scopes

### Available Scopes

| Scope | Description | Access Level | Example Operations |
|-------|-------------|--------------|-------------------|
| `trips:read` | View trip information | Read-only | GET /api/trips |
| `trips:write` | Create and modify trips | Read-write | POST /api/trips |
| `trips:delete` | Delete trips | Destructive | DELETE /api/trips/{id} |
| `flights:read` | Search flights | Read-only | POST /api/flights/search |
| `accommodations:read` | Search accommodations | Read-only | POST /api/accommodations/search |
| `chat:access` | Use AI chat features | Interactive | POST /api/chat/message |
| `memory:read` | Access user memory | Read-only | GET /api/memory/user |
| `memory:write` | Update user preferences | Read-write | PUT /api/memory/preferences |
| `webhooks:manage` | Manage webhooks | Admin | POST /api/webhooks |
| `admin:access` | Administrative functions | Admin | GET /api/admin/users |

### Scope Inheritance

Some scopes include others:

- `trips:write` includes `trips:read`
- `trips:delete` includes `trips:read` and `trips:write`
- `admin:access` includes all other scopes

### Checking Permissions

Verify current token permissions:

```http
GET /api/auth/permissions
Authorization: Bearer {token}
```

**Response (200 OK):**

```json
{
  "permissions": [
    "trips:read",
    "trips:write",
    "flights:read"
  ],
  "token_type": "api_key",
  "expires_at": "2026-01-15T10:30:00Z"
}
```

---

## Security Best Practices

### Token Security

#### 1. Secure Storage

- **Frontend**: Store tokens in httpOnly cookies or secure storage
- **Mobile**: Use keychain (iOS) or keystore (Android)
- **Server**: Use environment variables or secure vaults

#### 2. Token Rotation

```javascript
// Automatic token refresh
async function refreshTokenIfNeeded(token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  const expiresAt = payload.exp * 1000;
  
  if (Date.now() > expiresAt - 60000) { // Refresh 1 minute before expiry
    return await refreshToken();
  }
  
  return token;
}
```

#### 3. Secure Transmission

- Always use HTTPS in production
- Validate SSL certificates
- Use certificate pinning for mobile apps

### API Key Security

#### 1. Environment Variables

```bash
# .env file
TRIPSAGE_API_KEY=ts_live_1234567890abcdef
```

#### 2. IP Whitelisting

Restrict API key usage to specific IP addresses:

```json
{
  "ip_whitelist": [
    "192.168.1.0/24",
    "10.0.0.1",
    "203.0.113.0/24"
  ]
}
```

#### 3. Principle of Least Privilege

Grant only necessary permissions:

```json
{
  "permissions": [
    "flights:read",
    "accommodations:read"
  ]
}
```

### Rate Limiting Protection

#### 1. Implement Backoff

```javascript
async function apiRequestWithBackoff(url, options) {
  let delay = 1000;
  
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await fetch(url, options);
    
    if (response.status !== 429) {
      return response;
    }
    
    await new Promise(resolve => setTimeout(resolve, delay));
    delay *= 2;
  }
  
  throw new Error('Rate limit exceeded after retries');
}
```

#### 2. Monitor Usage

Track API usage to avoid limits:

```http
GET /api/user/usage
Authorization: Bearer {token}
```

---

## Rate Limiting

### Default Limits

| Authentication | Requests per Minute | Burst Limit | Daily Limit |
|---------------|-------------------|-------------|-------------|
| Unauthenticated | 10 | 20 | 100 |
| JWT Token | 100 | 200 | 10,000 |
| API Key (Basic) | 200 | 400 | 20,000 |
| API Key (Premium) | 1000 | 2000 | 100,000 |

### Rate Limit Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1642284000
X-RateLimit-Window: 60
X-RateLimit-Retry-After: 30
```

### Handling Rate Limits

```javascript
function handleRateLimit(response) {
  if (response.status === 429) {
    const retryAfter = response.headers.get('X-RateLimit-Retry-After');
    const resetTime = response.headers.get('X-RateLimit-Reset');
    
    console.log(`Rate limited. Retry after ${retryAfter} seconds`);
    console.log(`Limit resets at ${new Date(resetTime * 1000)}`);
    
    // Implement exponential backoff
    return new Promise(resolve => {
      setTimeout(() => resolve(fetch(url, options)), retryAfter * 1000);
    });
  }
  
  return response;
}
```

---

## Troubleshooting

### Common Authentication Issues

#### 1. Invalid Token Format

**Error:**

```json
{
  "error": true,
  "message": "Invalid token format",
  "code": "INVALID_TOKEN_FORMAT"
}
```

**Solution:**

- Ensure token starts with `Bearer`
- Check for extra spaces or characters
- Verify token is not truncated

#### 2. Expired Token

**Error:**

```json
{
  "error": true,
  "message": "Token has expired",
  "code": "TOKEN_EXPIRED"
}
```

**Solution:**

- Use refresh token to get new access token
- Implement automatic token refresh
- Check system clock synchronization

#### 3. Insufficient Permissions

**Error:**

```json
{
  "error": true,
  "message": "Insufficient permissions",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Solution:**

- Check required scopes for endpoint
- Update API key permissions
- Use token with appropriate scopes

#### 4. API Key Not Found

**Error:**

```json
{
  "error": true,
  "message": "API key not found",
  "code": "API_KEY_NOT_FOUND"
}
```

**Solution:**

- Verify API key is correct
- Check if key was revoked
- Ensure key hasn't expired

### Testing Authentication

#### 1. Validate Token

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.tripsage.ai/api/auth/validate"
```

#### 2. Check Permissions

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.tripsage.ai/api/auth/permissions"
```

#### 3. Test API Key

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.tripsage.ai/api/health"
```

### Debug Mode

Enable debug logging for authentication issues:

```javascript
const client = new TripSageClient({
  apiKey: 'your-api-key',
  debug: true // Enables detailed logging
});
```

---

---

## 🔗 Related Documentation

### Quick Links

- **[Getting Started Guide](getting-started.md)** - Setup and first API calls
- **[REST API Endpoints](rest-endpoints.md)** - Complete endpoint reference
- **[Error Codes](error-codes.md)** - Authentication error troubleshooting
- **[Quick Examples](usage-examples.md)** - Copy-paste authentication code
- **[Internal API Key Service Guide](../developers/api-key-service.md)** - Implementation details for developers

### Common Workflows

- **New to TripSage?** → Start with [Getting Started](getting-started.md)
- **Building an integration?** → Check [Complete Examples](examples.md)
- **Authentication failing?** → See [Error Troubleshooting](error-codes.md#authentication-errors)
- **Need real-time features?** → Explore [WebSocket API](websocket-api.md)

---

## Support

For authentication issues:

- **Documentation**: This authentication reference
- **Interactive Testing**: Use `/api/docs` for testing endpoints
- **Support**: <support@tripsage.ai>
- **Security Issues**: <security@tripsage.ai>

Include authentication details (without sensitive tokens) when reporting issues.
