#!/usr/bin/env python
"""
Test script for the TripSage API.

This script starts the FastAPI server and performs basic tests to
verify the API functionality.
"""

import asyncio
import os
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import httpx
import uvicorn
from dotenv import load_dotenv
from pydantic import BaseModel

from tripsage.api.main import app

# Add the project root to the path so we can import from src
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Constants
API_BASE_URL = "http://localhost:8000/api"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"


# Models for test data
class TestUser(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    auth_token: Optional[str] = None


class TestTrip(BaseModel):
    name: str
    start_date: date
    end_date: date
    destination: str
    budget: float
    travelers: int = 1
    id: Optional[str] = None


class TestFlight(BaseModel):
    trip_id: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    airline: Optional[str] = None
    price: float
    id: Optional[str] = None


async def initialize_db():
    """Initialize the database connection."""
    print("Initializing database...")
    from tripsage.db.initialize import initialize_databases

    success = await initialize_databases(run_migrations_on_startup=False)
    if not success:
        print("Failed to initialize database")
        sys.exit(1)
    print("Database initialized successfully")


async def register_user(client: httpx.AsyncClient, user: TestUser) -> bool:
    """Register a test user."""
    response = await client.post(
        f"{API_BASE_URL}/auth/register",
        json={
            "email": user.email,
            "password": user.password,
            "full_name": user.full_name,
        },
    )

    if response.status_code == 201:
        print(f"User {user.email} registered successfully")
        return True
    elif response.status_code == 400 and "already registered" in response.text:
        print(f"User {user.email} already exists, continuing with login")
        return True
    else:
        print(f"Failed to register user: {response.status_code} - {response.text}")
        return False


async def login_user(client: httpx.AsyncClient, user: TestUser) -> bool:
    """Login a test user and get an access token."""
    response = await client.post(
        f"{API_BASE_URL}/auth/token",
        data={"username": user.email, "password": user.password},
    )

    if response.status_code == 200:
        token_data = response.json()
        user.auth_token = token_data["access_token"]
        print(f"User {user.email} logged in successfully")
        return True
    else:
        print(f"Failed to login user: {response.status_code} - {response.text}")
        return False


async def create_trip(
    client: httpx.AsyncClient, user: TestUser, trip: TestTrip
) -> bool:
    """Create a test trip."""
    headers = {"Authorization": f"Bearer {user.auth_token}"}

    response = await client.post(
        f"{API_BASE_URL}/trips",
        headers=headers,
        json={
            "name": trip.name,
            "start_date": trip.start_date.isoformat(),
            "end_date": trip.end_date.isoformat(),
            "destination": trip.destination,
            "budget": trip.budget,
            "travelers": trip.travelers,
        },
    )

    if response.status_code == 201:
        trip_data = response.json()
        trip.id = trip_data["id"]
        print(f"Trip '{trip.name}' created successfully with ID {trip.id}")
        return True
    else:
        print(f"Failed to create trip: {response.status_code} - {response.text}")
        return False


async def get_trips(client: httpx.AsyncClient, user: TestUser) -> List[Dict]:
    """Get all trips for the user."""
    headers = {"Authorization": f"Bearer {user.auth_token}"}

    response = await client.get(
        f"{API_BASE_URL}/trips",
        headers=headers,
    )

    if response.status_code == 200:
        trips = response.json()
        print(f"Retrieved {len(trips)} trips for user {user.email}")
        return trips
    else:
        print(f"Failed to get trips: {response.status_code} - {response.text}")
        return []


async def create_flight(
    client: httpx.AsyncClient, user: TestUser, flight: TestFlight
) -> bool:
    """Create a test flight."""
    headers = {"Authorization": f"Bearer {user.auth_token}"}

    response = await client.post(
        f"{API_BASE_URL}/flights",
        headers=headers,
        json={
            "trip_id": flight.trip_id,
            "origin": flight.origin,
            "destination": flight.destination,
            "departure_time": flight.departure_time.isoformat(),
            "arrival_time": flight.arrival_time.isoformat(),
            "airline": flight.airline,
            "price": flight.price,
        },
    )

    if response.status_code == 201:
        flight_data = response.json()
        flight.id = flight_data["id"]
        print(
            f"Flight from {flight.origin} to {flight.destination} created "
            f"successfully with ID {flight.id}"
        )
        return True
    else:
        print(f"Failed to create flight: {response.status_code} - {response.text}")
        return False


async def get_flights_for_trip(
    client: httpx.AsyncClient, user: TestUser, trip_id: str
) -> List[Dict]:
    """Get all flights for a trip."""
    headers = {"Authorization": f"Bearer {user.auth_token}"}

    response = await client.get(
        f"{API_BASE_URL}/flights/trip/{trip_id}",
        headers=headers,
    )

    if response.status_code == 200:
        flights = response.json()
        print(f"Retrieved {len(flights)} flights for trip {trip_id}")
        return flights
    else:
        print(f"Failed to get flights: {response.status_code} - {response.text}")
        return []


async def run_tests():
    """Run a series of tests against the API."""
    try:
        # Initialize the database
        await initialize_db()

        # Create a test client
        async with httpx.AsyncClient() as client:
            # Create a test user
            test_user = TestUser(
                email=TEST_USER_EMAIL,
                password=TEST_USER_PASSWORD,
                full_name="Test User",
            )

            # Register and login the user
            if not await register_user(client, test_user):
                return
            if not await login_user(client, test_user):
                return

            # Create a test trip
            today = date.today()
            test_trip = TestTrip(
                name="Test Vacation",
                start_date=today + timedelta(days=30),
                end_date=today + timedelta(days=37),
                destination="Hawaii",
                budget=2000.0,
                travelers=2,
            )

            if not await create_trip(client, test_user, test_trip):
                return

            # Get all trips
            trips = await get_trips(client, test_user)
            if not trips:
                return

            # Create a test flight
            departure_time = datetime.combine(
                test_trip.start_date, datetime.min.time()
            ) + timedelta(hours=10)
            arrival_time = departure_time + timedelta(hours=6)

            test_flight = TestFlight(
                trip_id=test_trip.id,
                origin="SFO",
                destination="HNL",
                departure_time=departure_time,
                arrival_time=arrival_time,
                airline="Hawaiian Airlines",
                price=450.0,
            )

            if not await create_flight(client, test_user, test_flight):
                return

            # Get all flights for the trip
            flights = await get_flights_for_trip(client, test_user, test_trip.id)
            if not flights:
                return

            print("\nAll tests completed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")


async def main():
    """Main function to run the test script."""
    # Start the FastAPI server in a separate thread
    server_process = None
    try:
        print("Starting API server...")

        # Use uvicorn to start the server
        config = uvicorn.Config(app=app, host="127.0.0.1", port=8000, log_level="info")
        server = uvicorn.Server(config)

        # Start the server in a separate task
        server_task = asyncio.create_task(server.serve())

        # Wait for server to start
        time.sleep(1)

        # Run the tests
        await run_tests()

        # Stop the server
        print("Stopping API server...")
        server.should_exit = True
        await server_task
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Ensure server is stopped
        if server_process:
            server_process.terminate()


if __name__ == "__main__":
    asyncio.run(main())
