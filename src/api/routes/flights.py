from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.auth import User, get_current_active_user
from src.api.database import get_flight_repository, get_repository, get_trip_repository
from src.db.models.flight import BookingStatus
from src.db.models.flight import Flight as DBFlight
from src.db.repositories.flight import FlightRepository
from src.db.repositories.trip import TripRepository

router = APIRouter(
    prefix="/flights",
    tags=["flights"],
    dependencies=[Depends(get_current_active_user)],
)


# Flight models
class FlightBase(BaseModel):
    trip_id: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    airline: Optional[str] = None
    price: float
    booking_link: Optional[str] = None
    segment_number: Optional[int] = None
    booking_status: Optional[str] = "viewed"
    data_source: Optional[str] = None


class FlightCreate(FlightBase):
    pass


class FlightUpdate(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    airline: Optional[str] = None
    price: Optional[float] = None
    booking_link: Optional[str] = None
    segment_number: Optional[int] = None
    booking_status: Optional[str] = None
    data_source: Optional[str] = None


class FlightResponse(FlightBase):
    id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Convert DB model to API response
def db_flight_to_response(db_flight: DBFlight) -> FlightResponse:
    return FlightResponse(
        id=str(db_flight.id),
        trip_id=str(db_flight.trip_id),
        origin=db_flight.origin,
        destination=db_flight.destination,
        departure_time=db_flight.departure_time,
        arrival_time=db_flight.arrival_time,
        airline=db_flight.airline,
        price=db_flight.price,
        booking_link=db_flight.booking_link,
        segment_number=db_flight.segment_number,
        booking_status=(
            db_flight.booking_status.value if db_flight.booking_status else "viewed"
        ),
        data_source=db_flight.data_source,
        created_at=db_flight.created_at.isoformat() if db_flight.created_at else None,
        updated_at=db_flight.updated_at.isoformat() if db_flight.updated_at else None,
    )


# Verify trip access
async def verify_trip_access(
    trip_id: int, user_id: int, trip_repo: TripRepository
) -> bool:
    """
    Verify that a user has access to a trip.

    Args:
        trip_id: ID of the trip to verify access for
        user_id: ID of the user attempting to access
        trip_repo: Trip repository

    Returns:
        True if access is allowed, False otherwise

    Raises:
        HTTPException: If trip not found or access denied
    """
    trip = await trip_repo.get_by_id(trip_id)

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    if trip.user_id != user_id:
        # Check if admin
        # This would need to check if the user is an admin
        # For now, we'll just deny access if not the trip owner
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    return True


# Get all flights for a trip
@router.get("/trip/{trip_id}", response_model=List[FlightResponse])
async def get_flights_for_trip(
    trip_id: str,
    current_user: User = None,
    flight_repo: FlightRepository = None,
    trip_repo: TripRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if flight_repo is None:
        flight_repo = get_repository(get_flight_repository)()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()

    # Verify access to trip
    await verify_trip_access(int(trip_id), int(current_user.id), trip_repo)

    # Get flights
    flights = await flight_repo.find_by_trip_id(int(trip_id))
    return [db_flight_to_response(flight) for flight in flights]


# Get flight by ID
@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight(
    flight_id: str,
    current_user: User = None,
    flight_repo: FlightRepository = None,
    trip_repo: TripRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if flight_repo is None:
        flight_repo = get_repository(get_flight_repository)()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()

    # Get flight
    flight = await flight_repo.get_by_id(int(flight_id))
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found"
        )

    # Verify access to flight's trip
    await verify_trip_access(flight.trip_id, int(current_user.id), trip_repo)

    return db_flight_to_response(flight)


# Create new flight
@router.post("/", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
async def create_flight(
    flight_data: FlightCreate,
    current_user: User = None,
    flight_repo: FlightRepository = None,
    trip_repo: TripRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if flight_repo is None:
        flight_repo = get_repository(get_flight_repository)()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()

    # Verify access to trip
    await verify_trip_access(int(flight_data.trip_id), int(current_user.id), trip_repo)

    # Create flight object
    new_flight = DBFlight(
        trip_id=int(flight_data.trip_id),
        origin=flight_data.origin,
        destination=flight_data.destination,
        departure_time=flight_data.departure_time,
        arrival_time=flight_data.arrival_time,
        airline=flight_data.airline,
        price=flight_data.price,
        booking_link=flight_data.booking_link,
        segment_number=flight_data.segment_number,
        booking_status=(
            BookingStatus(flight_data.booking_status)
            if flight_data.booking_status
            else BookingStatus.VIEWED
        ),
        data_source=flight_data.data_source,
    )

    # Save to database
    created_flight = await flight_repo.create(new_flight)
    return db_flight_to_response(created_flight)


# Update flight
@router.patch("/{flight_id}", response_model=FlightResponse)
async def update_flight(
    flight_id: str,
    flight_update: FlightUpdate,
    current_user: User = None,
    flight_repo: FlightRepository = None,
    trip_repo: TripRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if flight_repo is None:
        flight_repo = get_repository(get_flight_repository)()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()

    # Get flight
    flight = await flight_repo.get_by_id(int(flight_id))
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found"
        )

    # Verify access to flight's trip
    await verify_trip_access(flight.trip_id, int(current_user.id), trip_repo)

    # Update flight fields
    if flight_update.origin is not None:
        flight.origin = flight_update.origin
    if flight_update.destination is not None:
        flight.destination = flight_update.destination
    if flight_update.departure_time is not None:
        flight.departure_time = flight_update.departure_time
    if flight_update.arrival_time is not None:
        flight.arrival_time = flight_update.arrival_time
    if flight_update.airline is not None:
        flight.airline = flight_update.airline
    if flight_update.price is not None:
        flight.price = flight_update.price
    if flight_update.booking_link is not None:
        flight.booking_link = flight_update.booking_link
    if flight_update.segment_number is not None:
        flight.segment_number = flight_update.segment_number
    if flight_update.booking_status is not None:
        flight.booking_status = BookingStatus(flight_update.booking_status)
    if flight_update.data_source is not None:
        flight.data_source = flight_update.data_source

    # Save updated flight
    updated_flight = await flight_repo.update(flight)
    return db_flight_to_response(updated_flight)


# Delete flight
@router.delete("/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flight(
    flight_id: str,
    current_user: User = None,
    flight_repo: FlightRepository = None,
    trip_repo: TripRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if flight_repo is None:
        flight_repo = get_repository(get_flight_repository)()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()

    # Get flight
    flight = await flight_repo.get_by_id(int(flight_id))
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found"
        )

    # Verify access to flight's trip
    await verify_trip_access(flight.trip_id, int(current_user.id), trip_repo)

    # Delete flight
    success = await flight_repo.delete(flight)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete flight"
        )

    return None
