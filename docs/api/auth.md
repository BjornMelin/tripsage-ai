# Authentication

The TripSage AI API uses JWT-based authentication with Supabase integration. All API requests require a valid Bearer token for authentication.

## Overview

Authentication is handled through Supabase's authentication system. Users authenticate with Supabase and receive a JWT token that must be included in all API requests.

## Getting Started

### 1. Create a Supabase Account

First, you need a Supabase account and project:

1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Note your project URL and anon key from the project settings

### 2. User Authentication

Users authenticate with Supabase using one of the supported methods:

- Email/password
- OAuth providers (Google, GitHub, etc.)
- Magic links
- Phone authentication

### 3. Obtain JWT Token

After authentication, Supabase provides a JWT access token. This token must be included in all API requests.

## API Authentication

### Bearer Token

Include the JWT token in the `Authorization` header:

```http
Authorization: Bearer <your-jwt-token>
```

### Example Request

```bash
curl -X GET "https://api.tripsage.ai/v1/trips" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Python Example

```python
import requests

headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.tripsage.ai/v1/trips", headers=headers)
```

### JavaScript Example

```javascript
const response = await fetch("https://api.tripsage.ai/v1/trips", {
  method: "GET",
  headers: {
    Authorization: `Bearer ${jwtToken}`,
    "Content-Type": "application/json",
  },
});
```

## Token Management

### Token Expiration

JWT tokens have an expiration time (typically 1 hour). When a token expires, you'll receive a `401 Unauthorized` response.

### Token Refresh

Supabase automatically handles token refresh. The client libraries provide methods to refresh tokens:

```javascript
// JavaScript/Supabase client
const { data, error } = await supabase.auth.refreshSession();
```

### Handling Expired Tokens

Implement proper error handling for expired tokens:

```python
response = requests.get(url, headers=headers)
if response.status_code == 401:
    # Token expired, refresh and retry
    new_token = refresh_token()
    headers["Authorization"] = f"Bearer {new_token}"
    response = requests.get(url, headers=headers)
```

## Security Best Practices

### Token Storage

- **Never store tokens in localStorage** (vulnerable to XSS)
- Use secure httpOnly cookies for server-side storage
- Use Supabase's built-in session management

### Token Transmission

- Always use HTTPS in production
- Include tokens in Authorization header, not query parameters
- Validate tokens on the server side

### Rate Limiting

The API implements rate limiting. Authenticated requests have higher limits than anonymous requests.

## Error Responses

### Invalid Token

```json
{
  "detail": "Invalid authentication credentials",
  "type": "authentication_error",
  "code": "AUTH001"
}
```

### Expired Token

```json
{
  "detail": "Token has expired",
  "type": "authentication_error",
  "code": "AUTH002"
}
```

### Missing Token

```json
{
  "detail": "Authentication credentials were not provided",
  "type": "authentication_error",
  "code": "AUTH003"
}
```

## Testing Authentication

### Development Environment

For local development, you can use the Supabase CLI:

```bash
# Start Supabase locally
supabase start

# Create a test user
supabase auth users create --email test@example.com --password password123
```

### API Key Authentication (Admin)

Some administrative endpoints may accept API keys instead of JWT tokens. These are configured server-side and should only be used for service-to-service communication.

## Troubleshooting

### Common Issues

1. **"Invalid authentication credentials"**

   - Check that the token is correctly formatted
   - Verify the token hasn't expired
   - Ensure you're using the correct Supabase project

2. **"Token has expired"**

   - Implement automatic token refresh
   - Handle the refresh flow gracefully in your application

3. **CORS issues**
   - Ensure your frontend is configured with the correct Supabase URL
   - Check CORS settings in Supabase dashboard

### Debug Mode

Enable debug logging to troubleshoot authentication issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

- [Quick Start Guide](usage-examples.md) - Code examples
- [API Reference](rest-endpoints.md) - Complete endpoint documentation
- [Error Codes](error-codes.md) - Error handling reference
