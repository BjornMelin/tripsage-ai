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
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/token` - Login and get access token
- `GET /auth/me` - Get current user profile

### Users
- `GET /users/` - Get all users (admin only)
- `GET /users/{user_id}` - Get user by ID
- `PATCH /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user

### Trips
- `GET /trips/` - Get all trips for current user
- `GET /trips/{trip_id}` - Get trip by ID
- `POST /trips/` - Create new trip
- `PATCH /trips/{trip_id}` - Update trip
- `DELETE /trips/{trip_id}` - Delete trip

### Flights
- `GET /flights/trip/{trip_id}` - Get all flights for a trip
- `GET /flights/{flight_id}` - Get flight by ID
- `POST /flights/` - Create new flight
- `PATCH /flights/{flight_id}` - Update flight
- `DELETE /flights/{flight_id}` - Delete flight

## Development

The API follows RESTful principles and uses JWT for authentication. All endpoints that require authentication expect a valid JWT token in the Authorization header.

### Adding New Routes

1. Create a new file in the `routes` directory
2. Define your router and endpoints
3. Import and include your router in `main.py`