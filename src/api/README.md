# TripSage API

FastAPI backend for the TripSage travel planning system.

## Setup

1. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials and other settings
   ```

4. Run the development server:

   ```bash
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/token` - Login and get access token
- `GET /api/auth/me` - Get current user profile

### Users

- `GET /api/users/` - Get all users (admin only)
- `GET /api/users/{user_id}` - Get user by ID
- `PATCH /api/users/{user_id}` - Update user
- `DELETE /api/users/{user_id}` - Delete user

### Trips

- `GET /api/trips/` - Get all trips for current user
- `GET /api/trips/{trip_id}` - Get trip by ID
- `POST /api/trips/` - Create new trip
- `PATCH /api/trips/{trip_id}` - Update trip
- `DELETE /api/trips/{trip_id}` - Delete trip

### Flights

- `GET /api/flights/trip/{trip_id}` - Get all flights for a trip
- `GET /api/flights/{flight_id}` - Get flight by ID
- `POST /api/flights/` - Create new flight
- `PATCH /api/flights/{flight_id}` - Update flight
- `DELETE /api/flights/{flight_id}` - Delete flight

## Architecture

The API follows a layered architecture:

1. **Routes Layer**: API endpoints and request/response models
2. **Repository Layer**: Data access and persistence through the repository pattern
3. **Model Layer**: Domain models with validation and business logic

## Database Access

The API interacts with the Supabase database using the repository pattern, which provides:

- Type-safe data models with validation via Pydantic
- Separation of concerns for data access
- Consistent error handling
- Abstractions for common database operations

## Authentication

The API uses JWT-based authentication with bearer tokens. To access protected endpoints, include an `Authorization` header with a valid JWT token:

```plaintext
Authorization: Bearer <token>
```

## Testing

A test script is provided to verify the API functionality:

```bash
python scripts/test_api.py
```

## Development

The API follows RESTful principles and uses JWT for authentication. All endpoints that require authentication expect a valid JWT token in the Authorization header.

### Adding New Routes

1. Create a new file in the `routes` directory
2. Define your router and endpoints
3. Import and include your router in `main.py`

### Adding New Models

1. Create a new file in the `db/models` directory
2. Define your model class extending `BaseDBModel`
3. Implement any needed validation or business logic

### Adding New Repositories

1. Create a new file in the `db/repositories` directory
2. Define your repository class extending `BaseRepository[YourModel]`
3. Implement any specialized query methods
4. Add your repository to the dependency system in `database.py`

## Environment Variables

The API requires the following environment variables:

```plaintext
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
JWT_SECRET_KEY=your-jwt-secret-key
```
