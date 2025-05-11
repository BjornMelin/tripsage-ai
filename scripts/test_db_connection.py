#!/usr/bin/env python
"""
TripSage Database Connection Test Script

This script tests the TripSage database connection and performs basic CRUD operations
using the implemented database layer.

Usage: python test_db_connection.py
"""

import asyncio
import os
import sys
from datetime import date, datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db import (
    BookingStatus,
    Flight,
    FlightRepository,
    Trip,
    TripRepository,
    TripStatus,
    TripType,
    UserRepository,
    close_database_connection,
    initialize_database,
)
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


async def test_connection() -> None:
    """Test the database connection and perform basic CRUD operations."""
    logger.info("Testing database connection...")

    try:
        # Initialize database connection
        success = await initialize_database(verify_connection=True)
        if not success:
            logger.error("Failed to initialize database connection")
            return

        logger.info("Database connection initialized successfully")

        # Create repositories
        user_repo = UserRepository()
        trip_repo = TripRepository()
        flight_repo = FlightRepository()

        # Get all users
        users = await user_repo.get_all()
        logger.info(f"Found {len(users)} users in the database")
        for user in users:
            logger.info(f"User: {user.id} - {user.name} ({user.email})")

        # Get all trips
        trips = await trip_repo.get_all()
        logger.info(f"Found {len(trips)} trips in the database")
        for trip in trips:
            logger.info(
                f"Trip: {trip.id} - {trip.name} to {trip.destination} ({trip.start_date} to {trip.end_date})"
            )

        # Get user by email
        if users:
            user = await user_repo.get_by_email(users[0].email)
            if user:
                logger.info(f"Found user by email: {user.name} ({user.email})")
                logger.info(f"User preferences: {user.full_preferences}")

        # Get trip by ID
        if trips:
            trip = await trip_repo.get_by_id(trips[0].id)
            if trip:
                logger.info(f"Found trip by ID: {trip.name} to {trip.destination}")
                logger.info(f"Trip duration: {trip.duration_days} days")
                logger.info(f"Budget per day: ${trip.budget_per_day:.2f}")
                logger.info(f"Budget per person: ${trip.budget_per_person:.2f}")
                logger.info(f"Is international: {trip.is_international}")

                # Get flights for this trip
                flights = await flight_repo.find_by_trip_id(trip.id)
                logger.info(f"Found {len(flights)} flights for this trip")
                for flight in flights:
                    logger.info(
                        f"Flight: {flight.origin} to {flight.destination} on {flight.airline}"
                    )
                    logger.info(f"Departure: {flight.departure_time}")
                    logger.info(f"Arrival: {flight.arrival_time}")
                    logger.info(f"Duration: {flight.duration_formatted}")
                    logger.info(f"Price: ${flight.price}")
                    logger.info(f"Is international: {flight.is_international}")

        # Test creating a new trip
        new_trip = Trip(
            name="Winter Gateway to Tokyo",
            start_date=date(2025, 12, 10),
            end_date=date(2025, 12, 20),
            destination="Tokyo, Japan",
            budget=5000.0,
            travelers=1,
            status=TripStatus.PLANNING,
            trip_type=TripType.SOLO,
            flexibility={"date_range": 5, "budget_range": 1000},
        )

        created_trip = await trip_repo.create(new_trip)
        logger.info(
            f"Created new trip: {created_trip.name} to {created_trip.destination}"
        )

        # Add a flight for the new trip
        new_flight = Flight(
            trip_id=created_trip.id,
            origin="SFO",
            destination="NRT",
            airline="ANA",
            departure_time=datetime(2025, 12, 10, 11, 0, 0),
            arrival_time=datetime(2025, 12, 11, 15, 30, 0),
            price=1200.0,
            booking_link="https://example.com/booking/flight456",
            booking_status=BookingStatus.VIEWED,
            data_source="Kayak API",
        )

        created_flight = await flight_repo.create(new_flight)
        logger.info(
            f"Created new flight: {created_flight.origin} to {created_flight.destination} on {created_flight.airline}"
        )

        # Update the trip
        created_trip.budget = 5500.0
        updated_trip = await trip_repo.update(created_trip)
        logger.info(f"Updated trip budget to: ${updated_trip.budget}")

        # Delete the test trip and flight to clean up
        await flight_repo.delete(created_flight.id)
        await trip_repo.delete(created_trip.id)
        logger.info("Deleted test trip and flight")

        logger.info("Database tests completed successfully")
    except Exception as e:
        logger.error(f"Error testing database connection: {e}")
        raise
    finally:
        # Close the database connection
        await close_database_connection()


if __name__ == "__main__":
    """Run the database test script."""
    try:
        asyncio.run(test_connection())
        print("Database test completed successfully")
    except Exception as e:
        print(f"Error testing database: {e}")
        exit(1)
