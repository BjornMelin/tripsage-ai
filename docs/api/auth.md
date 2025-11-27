# Auth

Authentication endpoints for user login and session management.

## `POST /api/auth/login`

Email/password login; returns JWT tokens and sets HttpOnly Supabase authentication cookies.

**Authentication**: Anonymous
**Rate Limit Key**: `login:failures:{ip}` and `login:failures:{email}` — 5 failed attempts per 15 minutes; returns HTTP 429 on excess

### Session & Authentication Model

- **Cookies**: The endpoint sets `HttpOnly` Supabase authentication cookies server-side. Clients with `credentials: "include"` (fetch) or default cookie handling (cURL) will automatically include them on subsequent requests.
- **Tokens**: The response includes `accessToken` (short-lived, typically 1 hour) and `refreshToken` for token-based clients.
- **rememberMe behavior**:
  - `true`: Access token TTL = 30 days, refresh token TTL = 60 days; tokens stored in localStorage recommended
  - `false` (default): Access token TTL = 1 hour, refresh token TTL = 7 days; tokens stored in sessionStorage recommended
- **Security note**: Use `rememberMe=false` for shared devices; always use HTTPS in production.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User email address |
| `password` | string | Yes | User password (min 8 chars) |
| `rememberMe` | boolean | No | Extend session lifetime and token expiration (default: false) |

### Response

`200 OK`

```json
{
  "accessToken": "eyJ...",
  "expiresIn": 3600,
  "refreshToken": "refresh_...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe"
  }
}
```

### Errors

- `400` - Invalid email or password format
  ```json
  {
    "error": "invalid_format",
    "message": "Email must be a valid email address and password must be at least 8 characters"
  }
  ```

- `401` - Invalid credentials
  ```json
  {
    "error": "invalid_credentials",
    "message": "Email or password is incorrect"
  }
  ```

- `429` - Too many failed login attempts
  ```json
  {
    "error": "rate_limit_exceeded",
    "message": "Too many failed login attempts. Please try again after 15 minutes.",
    "retryAfter": 900
  }
  ```
  Headers: `Retry-After: 900` (seconds)

### Examples

#### cURL

```bash
curl -X POST "http://localhost:3000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'
```

#### TypeScript

```typescript
const response = await fetch("http://localhost:3000/api/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "user@example.com",
    password: "securepass123",
  }),
});
const { accessToken, user } = await response.json();
```

#### Python

```python
import requests

response = requests.post(
    "http://localhost:3000/api/auth/login",
    json={"email": "user@example.com", "password": "securepass123"}
)
data = response.json()
```
