# Authentication Migration Plan

This document outlines the plan for migrating authentication functionality from the old API implementation to the new consolidated implementation. Authentication is a critical component of the API and requires careful handling during migration.

## Current Authentication Implementations

### Old Implementation (`/api/`)

The old implementation uses a combination of:

- JWT token-based authentication
- API key authentication
- Simple middleware-based authentication

Key files:

- `/api/middlewares/authentication.py` - Authentication middleware
- `/api/deps.py` - Authentication dependency functions
- `/api/routers/auth.py` - Authentication routes
- `/api/models/requests/auth.py` - Authentication request models
- `/api/models/responses/auth.py` - Authentication response models

### New Implementation (`/tripsage/api/`)

The new implementation uses:

- More structured JWT token authentication
- Role-based access control
- API key authentication with monitoring
- Modern middleware patterns

Key files:

- `/tripsage/api/middlewares/auth.py` - Authentication middleware
- `/tripsage/api/routers/auth.py` - Authentication routes (commented out)
- `/tripsage/api/models/auth.py` - Core authentication models
- `/tripsage/api/models/api_key.py` - API key models
- `/tripsage/api/models/requests/auth.py` - Authentication request models
- `/tripsage/api/models/responses/auth.py` - Authentication response models
- `/tripsage/api/services/auth.py` - Authentication service
- `/tripsage/api/services/key.py` - API key service

## Migration Strategy

### 1. Analyze Authentication Flow Differences

Before implementation, thoroughly compare the authentication flows between the old and new implementations:

1. **User Registration Flow**
   - Compare user registration endpoints
   - Compare validation and password hashing methods
   - Check for account activation/verification features

2. **Login Flow**
   - Compare login endpoints and token generation
   - Check for refresh token mechanisms
   - Analyze session management differences

3. **API Key Management**
   - Compare API key creation and validation
   - Check rate limiting and monitoring features
   - Analyze permissions and scope handling

4. **Protected Endpoint Access**
   - Compare how endpoints are protected
   - Analyze role-based access control mechanisms
   - Check for user information availability in request context

### 2. Authentication Middleware Migration

The new implementation uses a more advanced middleware pattern:

```python
# Old implementation in /api/middlewares/authentication.py
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Authentication logic
        # ...
        response = await call_next(request)
        return response

# New implementation in /tripsage/api/middlewares/auth.py
class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.token_expiry = settings.jwt_expiry_minutes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # More advanced authentication logic with settings injection
        # ...
        response = await call_next(request)
        return response
```

Migration actions:

1. Analyze and document all authentication checks in old middleware
2. Ensure new middleware covers all these checks
3. Update the new middleware if necessary
4. Update dependency functions to match new patterns

### 3. Authentication Service Migration

The new implementation uses dedicated services:

```python
# New implementation in /tripsage/api/services/auth.py
class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.token_expiry = settings.jwt_expiry_minutes
        self.refresh_token_expiry = settings.jwt_refresh_expiry_days

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        # User authentication logic
        # ...

    def create_access_token(self, data: Dict) -> str:
        # Token creation logic
        # ...

    def create_refresh_token(self, data: Dict) -> str:
        # Refresh token creation logic
        # ...

    async def validate_refresh_token(self, token: str) -> Optional[Dict]:
        # Token validation logic
        # ...
```

Migration actions:

1. Identify and document all authentication functions in old implementation
2. Ensure new service covers all these functions
3. Update the new service if necessary
4. Update any references to old authentication functions

### 4. API Key Service Migration

```python
# New implementation in /tripsage/api/services/key.py
class KeyService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.storage = get_dual_storage()

    async def create_api_key(self, user_id: str, name: str, scopes: List[str]) -> Dict:
        # API key creation logic
        # ...

    async def validate_api_key(self, api_key: str) -> Optional[Dict]:
        # API key validation logic
        # ...

    async def rotate_api_key(self, user_id: str, key_id: str) -> Dict:
        # API key rotation logic
        # ...
```

Migration actions:

1. Identify and document all API key functions in old implementation
2. Ensure new service covers all these functions
3. Update the new service if necessary
4. Update any references to old API key functions

### 5. Authentication Router Migration

The new implementation's authentication router is commented out:

```python
# app.include_router(auth.router, prefix="/api", tags=["auth"])
```

Migration actions:

1. Review the old authentication router in `/api/routers/auth.py`
2. Uncomment and update the new authentication router
3. Ensure all endpoints are implemented with correct dependencies
4. Update documentation and tests

### 6. Models Alignment

Ensure all authentication-related models are aligned:

```python
# Request models
LoginRequest
RegisterUserRequest
RefreshTokenRequest
ChangePasswordRequest
ForgotPasswordRequest
ResetPasswordRequest

# Response models
TokenResponse
UserResponse
```

Migration actions:

1. Compare model definitions between old and new implementations
2. Ensure all fields and validations are consistent
3. Update model references in services and routers

### 7. Testing Authentication Migration

Testing is critical for authentication:

```python
def test_login(test_client: TestClient, mock_auth_service, test_user):
    """Test user login."""
    # Configure mock service
    mock_auth_service.authenticate_user.return_value = test_user
    mock_auth_service.create_access_token.return_value = "test-token"
    mock_auth_service.create_refresh_token.return_value = "test-refresh-token"

    # Make request
    response = test_client.post(
        "/api/auth/login",
        json={"email": test_user["email"], "password": "test-password"},
    )

    # Check response
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

    # Verify service was called
    mock_auth_service.authenticate_user.assert_called_once()
```

Migration actions:

1. Create comprehensive tests for all authentication endpoints
2. Test both successful and failed authentication scenarios
3. Test API key authentication and JWT authentication
4. Test token expiration and refresh

## Migration Timeline

1. **Day 1**: Analyze authentication flow differences
2. **Day 2**: Middleware and dependency migration
3. **Day 3**: Service migration (AuthService and KeyService)
4. **Day 4**: Router migration
5. **Day 5**: Testing and validation

## Migration Risks and Mitigation

1. **Risk**: Breaking existing authentication for users
   - **Mitigation**: Perform thorough testing with both valid and invalid credentials
   - **Mitigation**: Consider a phased rollout with both systems running in parallel temporarily

2. **Risk**: Security vulnerabilities during transition
   - **Mitigation**: Perform security review of authentication implementation
   - **Mitigation**: Test for common vulnerabilities like token theft, CSRF, etc.

3. **Risk**: API key validation issues
   - **Mitigation**: Test all API key scenarios thoroughly
   - **Mitigation**: Monitor API key usage during transition

4. **Risk**: Session management differences
   - **Mitigation**: Document and test session handling thoroughly
   - **Mitigation**: Ensure all claims in JWTs are preserved

## Authentication Validation Checklist

- [ ] All authentication endpoints tested with valid credentials
- [ ] All authentication endpoints tested with invalid credentials
- [ ] API key authentication tested
- [ ] JWT token authentication tested
- [ ] Refresh token flow tested
- [ ] Role-based access control tested
- [ ] Session management tested
- [ ] Token expiration tested
- [ ] Security review completed

## Conclusion

Authentication migration requires careful planning and testing to ensure security is maintained and users are not affected. By following this plan, we can ensure that the authentication system is successfully migrated to the new consolidated implementation with minimal risk.

The new authentication implementation will provide improved security, better organization, and a more maintainable codebase.
