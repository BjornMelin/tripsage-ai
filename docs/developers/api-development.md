# 🔌 API Development Guide

> *Last updated: June 16, 2025*

This guide covers backend API development using FastAPI, including patterns, authentication, validation, and best practices for TripSage AI.

## 📋 Table of Contents

- [🔌 API Development Guide](#-api-development-guide)
  - [📋 Table of Contents](#-table-of-contents)
  - [🏗️ API Architecture](#️-api-architecture)
    - [**API Project Structure**](#api-project-structure)
    - [**FastAPI Application Setup**](#fastapi-application-setup)
  - [🔐 Authentication \& Authorization](#-authentication--authorization)
    - [**JWT Token Management**](#jwt-token-management)
    - [**Authentication Router**](#authentication-router)
  - [📝 Request/Response Models](#-requestresponse-models)
    - [**Pydantic Models with Validation**](#pydantic-models-with-validation)
  - [🛡️ Input Validation](#️-input-validation)
    - [**Validation Patterns**](#validation-patterns)
  - [⚠️ Error Handling](#️-error-handling)
    - [**Structured Error Responses**](#structured-error-responses)
  - [🚀 Performance Optimization](#-performance-optimization)
    - [**Caching Strategies**](#caching-strategies)
    - [**Database Query Optimization**](#database-query-optimization)
  - [📊 Streaming Responses](#-streaming-responses)
    - [**Server-Sent Events**](#server-sent-events)
    - [**Background Tasks**](#background-tasks)
  - [🔒 Security Best Practices](#-security-best-practices)
    - [**Input Sanitization**](#input-sanitization)
  - [🧪 Testing API Endpoints](#-testing-api-endpoints)
    - [**Test Structure**](#test-structure)
  - [📚 API Documentation](#-api-documentation)
    - [**OpenAPI Customization**](#openapi-customization)
  - [🔧 Common Patterns](#-common-patterns)
    - [**Service Layer Pattern**](#service-layer-pattern)
  - [🐛 Debugging Tips](#-debugging-tips)
    - [**Logging Configuration**](#logging-configuration)
    - [**Development Tools**](#development-tools)

## 🏗️ API Architecture

### **API Project Structure**

For the overall API project structure, see [docs/architecture/project-structure.md](../architecture/project-structure.md).

**Intended API Architecture:**

The API is designed to follow a modular architecture with clear separation of concerns:

```text
tripsage/api/
├── main.py              # FastAPI application entry point
├── core/
│   ├── config.py        # Configuration management
│   ├── dependencies.py  # Dependency injection
│   └── security.py      # Authentication utilities
├── routers/
│   ├── auth.py          # Authentication endpoints
│   ├── trips.py         # Trip management
│   ├── flights.py       # Flight search
│   ├── accommodations.py # Accommodation search
│   ├── chat.py          # AI chat interface
│   └── users.py         # User management
├── schemas/
│   ├── auth.py          # Authentication models
│   ├── trips.py         # Trip data models
│   └── common.py        # Shared models
├── services/
│   ├── auth_service.py  # Authentication logic
│   ├── trip_service.py  # Trip business logic
│   └── ai_service.py    # AI integration
└── middlewares/
    ├── authentication.py # Auth middleware
    ├── limiting.py  # SlowAPI configuration (rate limiting)
    └── cors.py          # CORS configuration
```

### **FastAPI Application Setup**

```python
# tripsage/api/main.py
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from tripsage.api.core.config import settings
from tripsage.api.routers import (
    auth, trips, flights, accommodations, chat, users
)
from tripsage.api.middlewares.authentication import AuthenticationMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    print("🚀 Starting TripSage API...")
    await initialize_database()
    await initialize_cache()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down TripSage API...")
    await cleanup_resources()

app = FastAPI(
    title="TripSage AI API",
    description="Intelligent travel planning platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthenticationMiddleware)
# Rate limiting is installed via SlowAPI in tripsage/api/limiting.py
# install_rate_limiting(app)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(trips.router, prefix="/api/trips", tags=["Trips"])
app.include_router(flights.router, prefix="/api/flights", tags=["Flights"])
app.include_router(accommodations.router, prefix="/api/accommodations", tags=["Accommodations"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI Chat"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(
        "tripsage.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_level="info"
    )
```

## 🔐 Authentication & Authorization

### **JWT Token Management**

```python
# tripsage/api/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import bcrypt

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes

    def create_access_token(self, data: dict) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

auth_service = AuthService()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user."""
    payload = auth_service.verify_token(credentials.credentials)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# Permission-based authorization
class Permission(str, Enum):
    READ_TRIPS = "trips:read"
    WRITE_TRIPS = "trips:write"
    DELETE_TRIPS = "trips:delete"
    ADMIN_ACCESS = "admin:access"

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user or not has_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### **Authentication Router**

```python
# tripsage/api/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from tripsage.api.schemas.auth import (
    UserCreate, UserLogin, Token, UserResponse
)
from tripsage.api.core.security import auth_service, get_current_user

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register new user."""
    # Check if user exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = auth_service.hash_password(user_data.password)
    user = await create_user({
        **user_data.dict(exclude={"password"}),
        "hashed_password": hashed_password
    })
    
    return UserResponse.from_orm(user)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return token."""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse.from_orm(current_user)

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token."""
    access_token = auth_service.create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email}
    )
    
    return Token(access_token=access_token, token_type="bearer")
```

## 📝 Request/Response Models

### **Pydantic Models with Validation**

```python
# tripsage_core/models/api/trip_models.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
from uuid import UUID

class TripStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DestinationCreate(BaseModel):
    """Destination creation model."""
    name: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=2, max_length=50)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    arrival_date: Optional[date] = None
    departure_date: Optional[date] = None
    
    @validator('departure_date')
    def departure_after_arrival(cls, v, values):
        if v and values.get('arrival_date') and v <= values['arrival_date']:
            raise ValueError('Departure date must be after arrival date')
        return v

class TripCreate(BaseModel):
    """Trip creation model."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    start_date: date = Field(...)
    end_date: date = Field(...)
    budget: Optional[float] = Field(None, gt=0)
    currency: str = Field(default="USD", regex=r"^[A-Z]{3}$")
    destinations: List[DestinationCreate] = Field(..., min_items=1)
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        if v <= values.get('start_date'):
            raise ValueError('End date must be after start date')
        return v
    
    @validator('destinations')
    def validate_destinations(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 destinations allowed')
        return v

class TripUpdate(BaseModel):
    """Trip update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = Field(None, gt=0)
    status: Optional[TripStatus] = None
    preferences: Optional[Dict[str, Any]] = None

class TripResponse(BaseModel):
    """Trip response model."""
    id: UUID
    name: str
    description: Optional[str]
    start_date: date
    end_date: date
    budget: Optional[float]
    currency: str
    status: TripStatus
    destinations: List[DestinationResponse]
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```

## 🛡️ Input Validation

### **Validation Patterns**

```python
# tripsage/api/schemas/common.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Union
import re

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, le=1000)
    size: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

class SearchParams(BaseModel):
    """Search parameters with validation."""
    query: Optional[str] = Field(None, min_length=1, max_length=200)
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    sort_by: Optional[str] = Field(None, regex=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    sort_order: Optional[str] = Field(default="asc", regex=r"^(asc|desc)$")
    
    @validator('query')
    def sanitize_query(cls, v):
        if v:
            # Remove potentially dangerous characters
            return re.sub(r'[<>"\';]', '', v.strip())
        return v

class FlightSearchParams(BaseModel):
    """Flight search parameters."""
    origin: str = Field(..., min_length=3, max_length=3, regex=r"^[A-Z]{3}$")
    destination: str = Field(..., min_length=3, max_length=3, regex=r"^[A-Z]{3}$")
    departure_date: date = Field(...)
    return_date: Optional[date] = None
    passengers: int = Field(default=1, ge=1, le=9)
    cabin_class: str = Field(default="economy", regex=r"^(economy|premium|business|first)$")
    
    @validator('departure_date')
    def departure_not_past(cls, v):
        if v < date.today():
            raise ValueError('Departure date cannot be in the past')
        return v
    
    @validator('return_date')
    def return_after_departure(cls, v, values):
        if v and v <= values.get('departure_date'):
            raise ValueError('Return date must be after departure date')
        return v
    
    @root_validator
    def validate_trip_type(cls, values):
        origin = values.get('origin')
        destination = values.get('destination')
        
        if origin == destination:
            raise ValueError('Origin and destination cannot be the same')
        
        return values
```

## ⚠️ Error Handling

### **Structured Error Responses**

```python
# tripsage/api/core/exceptions.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

class TripSageException(Exception):
    """Base exception for TripSage API."""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class BusinessLogicError(TripSageException):
    """Business logic validation error."""
    pass

class ExternalServiceError(TripSageException):
    """External service integration error."""
    pass

class RateLimitExceeded(TripSageException):
    """Rate limit exceeded error."""
    pass

async def tripsage_exception_handler(request: Request, exc: TripSageException):
    """Handle custom TripSage exceptions."""
    logger.exception(f"TripSage error: {exc.message}", exc_info=True)
    
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "message": exc.message,
                "code": exc.error_code or "BUSINESS_LOGIC_ERROR",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url)
            }
        }
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "Validation failed",
                "code": "VALIDATION_ERROR",
                "details": errors,
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url)
            }
        }
    )

async def http_exception_handler_custom(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "code": f"HTTP_{exc.status_code}",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url)
            }
        }
    )

# Register exception handlers
app.add_exception_handler(TripSageException, tripsage_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler_custom)
```

## 🚀 Performance Optimization

### **Caching Strategies**

```python
# tripsage/api/core/cache.py
from functools import wraps
import json
import hashlib
from typing import Any, Optional, Callable
from tripsage_core.services.infrastructure.cache_service import CacheService

cache_service = CacheService()

def cache_result(ttl: int = 3600, key_prefix: str = "api"):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            key_data = {
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            key_hash = hashlib.md5(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            cache_key = f"{key_prefix}:{func.__name__}:{key_hash}"
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator

# Usage example
@cache_result(ttl=3600, key_prefix="flights")
async def search_flights_cached(search_params: FlightSearchParams) -> List[Flight]:
    """Cached flight search."""
    return await duffel_client.search_flights(search_params)
```

### **Database Query Optimization**

```python
# tripsage/api/services/trip_service.py
from sqlalchemy import select, joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession

class TripService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_trip_with_details(self, trip_id: UUID, user_id: UUID) -> Optional[Trip]:
        """Get trip with all related data in single query."""
        query = (
            select(TripModel)
            .options(
                joinedload(TripModel.destinations),
                selectinload(TripModel.flights),
                selectinload(TripModel.accommodations),
                joinedload(TripModel.user)
            )
            .where(
                and_(
                    TripModel.id == trip_id,
                    TripModel.user_id == user_id
                )
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_trips_paginated(
        self,
        user_id: UUID,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Trip], int]:
        """Get paginated user trips with total count."""
        # Build base query
        query = select(TripModel).where(TripModel.user_id == user_id)
        
        # Apply filters
        if filters:
            if status := filters.get('status'):
                query = query.where(TripModel.status == status)
            if start_date := filters.get('start_date_from'):
                query = query.where(TripModel.start_date >= start_date)
            if end_date := filters.get('start_date_to'):
                query = query.where(TripModel.start_date <= end_date)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = (
            query
            .order_by(TripModel.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.size)
        )
        
        result = await self.db.execute(query)
        trips = result.scalars().all()
        
        return trips, total
```

## 📊 Streaming Responses

### **Server-Sent Events**

```python
# tripsage/api/routers/chat.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json

router = APIRouter()

async def stream_chat_response(
    message: str,
    trip_id: str,
    user_id: str
) -> AsyncGenerator[str, None]:
    """Stream AI chat response."""
    
    yield "data: {\"type\": \"start\", \"message\": \"Processing your request...\"}\n\n"
    
    try:
        # Initialize AI agent
        agent = await get_chat_agent(trip_id, user_id)
        
        # Stream response chunks
        async for chunk in agent.stream_response(message):
            data = {
                "type": "chunk",
                "content": chunk.content,
                "metadata": chunk.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(data)}\n\n"
        
        yield "data: {\"type\": \"complete\", \"message\": \"Response complete\"}\n\n"
        
    except Exception as e:
        error_data = {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(error_data)}\n\n"

@router.post("/trips/{trip_id}/chat/stream")
async def stream_chat(
    trip_id: str,
    message: ChatMessage,
    current_user: User = Depends(get_current_user)
):
    """Stream AI chat response using Server-Sent Events."""
    return StreamingResponse(
        stream_chat_response(message.content, trip_id, current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

### **Background Tasks**

```python
# tripsage/api/routers/trips.py
from fastapi import BackgroundTasks

async def process_trip_optimization(trip_id: str, user_id: str):
    """Process trip optimization in background."""
    try:
        # Heavy computation
        optimizer = TripOptimizer()
        optimized_itinerary = await optimizer.optimize_trip(trip_id)
        
        # Update database
        await update_trip_optimization_results(trip_id, optimized_itinerary)
        
        # Notify listeners via Supabase Realtime only (publisher helper handles details)
        await publish_realtime_update(
            channel=f"user:{user_id}",
            event="optimization_complete",
            payload={"trip_id": trip_id, "data": optimized_itinerary},
        )

    except Exception as e:
        logger.exception("Trip optimization failed", exc_info=e)
        await publish_realtime_update(
            channel=f"user:{user_id}",
            event="optimization_error",
            payload={"trip_id": trip_id, "error": str(e)},
        )

@router.post("/trips/{trip_id}/optimize")
async def optimize_trip(
    trip_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Start trip optimization in background."""
    background_tasks.add_task(
        process_trip_optimization,
        trip_id,
        current_user.id
    )
    
    return {
        "message": "Optimization started",
        "status": "processing",
        "trip_id": trip_id
    }
```

## 🔒 Security Best Practices

### **Input Sanitization**

```python
# tripsage/api/core/security.py
import re
from typing import Any, Dict

class InputSanitizer:
    """Sanitize user inputs to prevent security vulnerabilities."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not value:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';\\]', '', value.strip())
        
        # Limit length
        return sanitized[:max_length]
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputSanitizer.sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized

# Rate limiting implementation
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for identifier."""
        now = time()
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        
        return False
```

## 🧪 Testing API Endpoints

### **Test Structure**

```python
# tests/unit/api/routers/test_trips_router.py
import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
class TestTripsRouter:
    """Test trips API endpoints."""
    
    async def test_create_trip_success(
        self,
        async_client: AsyncClient,
        authenticated_user_headers: dict
    ):
        """Test successful trip creation."""
        trip_data = {
            "name": "European Adventure",
            "description": "A wonderful trip across Europe",
            "start_date": "2025-07-01",
            "end_date": "2025-07-15",
            "budget": 5000.0,
            "currency": "USD",
            "destinations": [
                {
                    "name": "Paris",
                    "country": "France",
                    "arrival_date": "2025-07-01",
                    "departure_date": "2025-07-05"
                },
                {
                    "name": "Rome",
                    "country": "Italy",
                    "arrival_date": "2025-07-05",
                    "departure_date": "2025-07-10"
                }
            ]
        }
        
        response = await async_client.post(
            "/api/trips",
            json=trip_data,
            headers=authenticated_user_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert data["name"] == trip_data["name"]
        assert data["status"] == "draft"
        assert len(data["destinations"]) == 2
        assert "id" in data
        assert "created_at" in data
    
    async def test_create_trip_validation_error(
        self,
        async_client: AsyncClient,
        authenticated_user_headers: dict
    ):
        """Test trip creation with validation errors."""
        invalid_trip_data = {
            "name": "",  # Empty name should fail
            "start_date": "2025-07-15",
            "end_date": "2025-07-01",  # End before start should fail
            "destinations": []  # Empty destinations should fail
        }
        
        response = await async_client.post(
            "/api/trips",
            json=invalid_trip_data,
            headers=authenticated_user_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]
    
    async def test_get_trip_unauthorized(self, async_client: AsyncClient):
        """Test getting trip without authentication."""
        response = await async_client.get("/api/trips/123")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.parametrize("trip_status", ["draft", "planning", "confirmed"])
    async def test_update_trip_status(
        self,
        async_client: AsyncClient,
        authenticated_user_headers: dict,
        sample_trip_id: str,
        trip_status: str
    ):
        """Test updating trip status."""
        update_data = {"status": trip_status}
        
        response = await async_client.patch(
            f"/api/trips/{sample_trip_id}",
            json=update_data,
            headers=authenticated_user_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["status"] == trip_status
```

## 📚 API Documentation

### **OpenAPI Customization**

```python
# tripsage/api/core/docs.py
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="TripSage AI API",
        version="1.0.0",
        description="""
        ## TripSage AI Travel Planning API
        
        Intelligent travel planning platform with AI-powered recommendations.
        
        ### Features
        - 🤖 AI-powered trip planning
        - ✈️ Flight search and booking
        - 🏨 Accommodation recommendations
        - 💬 Interactive chat interface
        - 📊 Trip optimization
        
        ### Authentication
        All endpoints require JWT authentication. Include the token in the Authorization header:
        ```
        Authorization: Bearer <your_token>
        ```
        
        ### Rate Limiting
        API requests are rate limited to 100 requests per minute per user.
        
        ### Error Handling
        All errors follow a consistent format with error codes and detailed messages.
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    # Add custom tags
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User authentication and authorization"
        },
        {
            "name": "Trips",
            "description": "Trip management and planning"
        },
        {
            "name": "Flights",
            "description": "Flight search and booking"
        },
        {
            "name": "Accommodations",
            "description": "Hotel and accommodation search"
        },
        {
            "name": "AI Chat",
            "description": "Interactive AI travel assistant"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## 🔧 Common Patterns

### **Service Layer Pattern**

```python
# tripsage/api/services/base_service.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

class BaseService(Generic[T], ABC):
    """Base service class with common CRUD operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @abstractmethod
    async def create(self, data: dict) -> T:
        """Create new entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def update(self, entity_id: UUID, data: dict) -> Optional[T]:
        """Update entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity."""
        pass
    
    @abstractmethod
    async def list(self, **filters) -> List[T]:
        """List entities with filters."""
        pass

# Implementation example
class TripService(BaseService[Trip]):
    """Trip service implementation."""
    
    async def create(self, data: dict) -> Trip:
        """Create new trip."""
        trip = TripModel(**data)
        self.db.add(trip)
        await self.db.commit()
        await self.db.refresh(trip)
        return trip
    
    async def get_by_id(self, trip_id: UUID) -> Optional[Trip]:
        """Get trip by ID."""
        query = select(TripModel).where(TripModel.id == trip_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
```

## 🐛 Debugging Tips

### **Logging Configuration**

```python
# tripsage/api/core/logging.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configure structured logging."""
    
    # Create formatter
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        extra={
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client_ip": request.client.host
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": process_time
        }
    )
    
    return response
```

### **Development Tools**

```python
# tripsage/api/core/debug.py
from fastapi import Request
import traceback

@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    """Debug middleware for development."""
    if settings.debug:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.exception(
                "Unhandled exception",
                extra={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "request_url": str(request.url),
                    "request_method": request.method
                }
            )
            raise
    else:
        return await call_next(request)

# Database query debugging
if settings.debug:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
```

---

This API development guide provides patterns and best practices for building robust, secure, and performant FastAPI applications. Follow these guidelines to maintain consistency and quality across the TripSage AI codebase.
