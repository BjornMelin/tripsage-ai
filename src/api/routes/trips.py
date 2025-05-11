from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.auth import User, get_current_active_user
from src.api.database import get_repository, get_trip_repository, get_user_repository
from src.db.models.trip import Trip as DBTrip
from src.db.models.trip import TripStatus, TripType
from src.db.repositories.trip import TripRepository
from src.db.repositories.user import UserRepository

router = APIRouter(
    prefix="/trips",
    tags=["trips"],
    dependencies=[Depends(get_current_active_user)],
)


# Trip models
class TripBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    destination: str
    budget: float
    travelers: int = 1
    trip_type: Optional[str] = "leisure"
    status: Optional[str] = "planning"
    flexibility: Optional[Dict[str, Any]] = None


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    destination: Optional[str] = None
    budget: Optional[float] = None
    travelers: Optional[int] = None
    trip_type: Optional[str] = None
    status: Optional[str] = None
    flexibility: Optional[Dict[str, Any]] = None


class TripResponse(TripBase):
    id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Convert DB model to API response
def db_trip_to_response(db_trip: DBTrip) -> TripResponse:
    return TripResponse(
        id=str(db_trip.id),
        name=db_trip.name,
        start_date=db_trip.start_date,
        end_date=db_trip.end_date,
        destination=db_trip.destination,
        budget=db_trip.budget,
        travelers=db_trip.travelers,
        trip_type=db_trip.trip_type.value if db_trip.trip_type else "leisure",
        status=db_trip.status.value if db_trip.status else "planning",
        flexibility=db_trip.flexibility,
        created_at=db_trip.created_at.isoformat() if db_trip.created_at else None,
        updated_at=db_trip.updated_at.isoformat() if db_trip.updated_at else None,
    )


# Get all trips for current user
@router.get("/", response_model=List[TripResponse])
async def get_trips(
    current_user: User = None,
    trip_repo: TripRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()
        
    # Find trips where user_id matches current user
    trips = await trip_repo.find_by_user_id(int(current_user.id))
    return [db_trip_to_response(trip) for trip in trips]


# Get trip by ID
@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: str,
    current_user: User = None,
    trip_repo: TripRepository = None,
    user_repo: UserRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()
        
    # Get trip
    trip = await trip_repo.get_by_id(int(trip_id))
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    # Check if user has access to this trip
    if trip.user_id != int(current_user.id):
        # Admin check
        current_user_db = await user_repo.get_by_id(int(current_user.id))
        if not current_user_db or not current_user_db.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    return db_trip_to_response(trip)


# Create new trip
@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_data: TripCreate,
    current_user: User = None,
    trip_repo: TripRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()
        
    # Create trip object
    new_trip = DBTrip(
        name=trip_data.name,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        destination=trip_data.destination,
        budget=trip_data.budget,
        travelers=trip_data.travelers,
        trip_type=(
            TripType(trip_data.trip_type) if trip_data.trip_type else TripType.LEISURE
        ),
        status=(
            TripStatus(trip_data.status) if trip_data.status else TripStatus.PLANNING
        ),
        flexibility=trip_data.flexibility,
        user_id=int(current_user.id),
    )

    # Save to database
    created_trip = await trip_repo.create(new_trip)
    return db_trip_to_response(created_trip)


# Update trip
@router.patch("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: str,
    trip_update: TripUpdate,
    current_user: User = None,
    trip_repo: TripRepository = None,
    user_repo: UserRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()
        
    # Get existing trip
    trip = await trip_repo.get_by_id(int(trip_id))
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    # Check if user has access to this trip
    if trip.user_id != int(current_user.id):
        # Admin check
        current_user_db = await user_repo.get_by_id(int(current_user.id))
        if not current_user_db or not current_user_db.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Update trip fields
    if trip_update.name is not None:
        trip.name = trip_update.name
    if trip_update.start_date is not None:
        trip.start_date = trip_update.start_date
    if trip_update.end_date is not None:
        trip.end_date = trip_update.end_date
    if trip_update.destination is not None:
        trip.destination = trip_update.destination
    if trip_update.budget is not None:
        trip.budget = trip_update.budget
    if trip_update.travelers is not None:
        trip.travelers = trip_update.travelers
    if trip_update.trip_type is not None:
        trip.trip_type = TripType(trip_update.trip_type)
    if trip_update.status is not None:
        trip.status = TripStatus(trip_update.status)
    if trip_update.flexibility is not None:
        trip.flexibility = trip_update.flexibility

    # Save updated trip
    updated_trip = await trip_repo.update(trip)
    return db_trip_to_response(updated_trip)


# Delete trip
@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: str,
    current_user: User = None,
    trip_repo: TripRepository = None,
    user_repo: UserRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if trip_repo is None:
        trip_repo = get_repository(get_trip_repository)()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()
    
    # Get trip
    trip = await trip_repo.get_by_id(int(trip_id))
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    # Check if user has access to this trip
    if trip.user_id != int(current_user.id):
        # Admin check
        current_user_db = await user_repo.get_by_id(int(current_user.id))
        if not current_user_db or not current_user_db.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Delete trip
    success = await trip_repo.delete(trip)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete trip"
        )

    return None
