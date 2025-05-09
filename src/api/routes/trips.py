from datetime import date
from typing import Any, Dict, List, Optional

from auth import User, get_current_active_user
from database import get_supabase_client
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(
    prefix="/trips",
    tags=["trips"],
    dependencies=[Depends(get_current_active_user)],
)


# Trip models
class TripBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    destination: str
    budget: Optional[float] = None
    preferences: Optional[Dict[str, Any]] = None


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    destination: Optional[str] = None
    budget: Optional[float] = None
    preferences: Optional[Dict[str, Any]] = None


class TripResponse(TripBase):
    id: str
    user_id: str
    created_at: str
    updated_at: str


# Get all trips for current user
@router.get("/", response_model=List[TripResponse])
async def get_trips(current_user: User = Depends(get_current_active_user)):
    supabase = get_supabase_client()
    response = (
        supabase.from_("trips").select("*").eq("user_id", current_user.id).execute()
    )
    return response.data


# Get trip by ID
@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: str, current_user: User = Depends(get_current_active_user)):
    supabase = get_supabase_client()
    response = supabase.from_("trips").select("*").eq("id", trip_id).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    # Check if user has access to this trip
    if response.data[0]["user_id"] != current_user.id:
        # Admin check
        admin_response = (
            supabase.from_("users")
            .select("is_admin")
            .eq("id", current_user.id)
            .execute()
        )
        if not admin_response.data or not admin_response.data[0].get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    return response.data[0]


# Create new trip
@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip: TripCreate, current_user: User = Depends(get_current_active_user)
):
    trip_data = trip.dict()
    trip_data["user_id"] = current_user.id

    supabase = get_supabase_client()
    response = supabase.from_("trips").insert(trip_data).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not create trip"
        )

    return response.data[0]


# Update trip
@router.patch("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: str,
    trip_update: TripUpdate,
    current_user: User = Depends(get_current_active_user),
):
    # Check if trip exists and user has access
    supabase = get_supabase_client()
    response = supabase.from_("trips").select("*").eq("id", trip_id).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    # Check if user has access to this trip
    if response.data[0]["user_id"] != current_user.id:
        # Admin check
        admin_response = (
            supabase.from_("users")
            .select("is_admin")
            .eq("id", current_user.id)
            .execute()
        )
        if not admin_response.data or not admin_response.data[0].get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Update trip
    update_data = trip_update.dict(exclude_unset=True)
    update_response = (
        supabase.from_("trips").update(update_data).eq("id", trip_id).execute()
    )

    if not update_response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not update trip"
        )

    return update_response.data[0]


# Delete trip
@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: str, current_user: User = Depends(get_current_active_user)
):
    # Check if trip exists and user has access
    supabase = get_supabase_client()
    response = supabase.from_("trips").select("*").eq("id", trip_id).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    # Check if user has access to this trip
    if response.data[0]["user_id"] != current_user.id:
        # Admin check
        admin_response = (
            supabase.from_("users")
            .select("is_admin")
            .eq("id", current_user.id)
            .execute()
        )
        if not admin_response.data or not admin_response.data[0].get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Delete trip
    delete_response = supabase.from_("trips").delete().eq("id", trip_id).execute()

    return None
